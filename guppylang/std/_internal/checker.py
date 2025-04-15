import ast
from dataclasses import dataclass
from typing import ClassVar, cast

from typing_extensions import assert_never

from guppylang.ast_util import get_type, with_loc, with_type
from guppylang.checker.core import Context
from guppylang.checker.errors.generic import ExpectedError, UnsupportedError
from guppylang.checker.errors.type_errors import (
    ArrayComprUnknownSizeError,
    TypeMismatchError,
)
from guppylang.checker.expr_checker import (
    ExprChecker,
    ExprSynthesizer,
    check_num_args,
    check_type_against,
    synthesize_call,
    synthesize_comprehension,
)
from guppylang.definition.custom import (
    CustomCallChecker,
)
from guppylang.definition.struct import CheckedStructDef, RawStructDef
from guppylang.diagnostic import Error, Note
from guppylang.error import GuppyError, GuppyTypeError, InternalGuppyError
from guppylang.nodes import (
    BarrierExpr,
    DesugaredArrayComp,
    DesugaredGeneratorExpr,
    ExitKind,
    GenericParamValue,
    GlobalCall,
    MakeIter,
    PanicExpr,
    ResultExpr,
)
from guppylang.tys.arg import ConstArg, TypeArg
from guppylang.tys.builtin import (
    array_type,
    array_type_def,
    bool_type,
    get_element_type,
    get_iter_size,
    int_type,
    is_array_type,
    is_bool_type,
    is_sized_iter_type,
    nat_type,
    sized_iter_type,
    string_type,
)
from guppylang.tys.const import Const, ConstValue
from guppylang.tys.subst import Subst
from guppylang.tys.ty import (
    FuncInput,
    FunctionType,
    InputFlags,
    NoneType,
    NumericType,
    StructType,
    Type,
    unify,
)


class ReversingChecker(CustomCallChecker):
    """Call checker for reverse arithmetic methods.

    For examples, turns a call to `__radd__` into a call to `__add__` with reversed
    arguments.
    """

    def parse_name(self) -> str:
        # Must be a dunder method
        assert self.func.name.startswith("__")
        assert self.func.name.endswith("__")
        name = self.func.name[2:-2]
        # Remove the `r`
        assert name.startswith("r")
        return f"__{name[1:]}__"

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        [self_arg, other_arg] = args
        self_arg, self_ty = ExprSynthesizer(self.ctx).synthesize(self_arg)
        f = self.ctx.globals.get_instance_func(self_ty, self.parse_name())
        assert f is not None
        return f.synthesize_call([other_arg, self_arg], self.node, self.ctx)


class UnsupportedChecker(CustomCallChecker):
    """Call checker for Python builtin functions that are not available in Guppy.

    Gives the uses a nicer error message when they try to use an unsupported feature.
    """

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        err = UnsupportedError(
            self.node, f"Builtin method `{self.func.name}`", singular=True
        )
        raise GuppyError(err)

    def check(self, args: list[ast.expr], ty: Type) -> tuple[ast.expr, Subst]:
        err = UnsupportedError(
            self.node, f"Builtin method `{self.func.name}`", singular=True
        )
        raise GuppyError(err)


class DunderChecker(CustomCallChecker):
    """Call checker for builtin functions that call out to dunder instance methods"""

    dunder_name: str
    num_args: int

    def __init__(self, dunder_name: str, num_args: int = 1):
        assert num_args > 0
        self.dunder_name = dunder_name
        self.num_args = num_args

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        check_num_args(self.num_args, len(args), self.node)
        fst, *rest = args
        return ExprSynthesizer(self.ctx).synthesize_instance_func(
            fst,
            rest,
            self.dunder_name,
            f"a valid argument to `{self.func.name}`",
            give_reason=True,
        )


class CallableChecker(CustomCallChecker):
    """Call checker for the builtin `callable` function"""

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        check_num_args(1, len(args), self.node)
        [arg] = args
        arg, ty = ExprSynthesizer(self.ctx).synthesize(arg)
        is_callable = (
            isinstance(ty, FunctionType)
            or self.ctx.globals.get_instance_func(ty, "__call__") is not None
        )
        const = with_loc(self.node, ast.Constant(value=is_callable))
        return const, bool_type()


class ArrayCopyChecker(CustomCallChecker):
    """Function call checker for the `array.copy` function."""

    @dataclass(frozen=True)
    class NonCopyableElementsError(Error):
        title: ClassVar[str] = "Non-copyable elements"
        span_label: ClassVar[str] = "Elements of type `{ty}` cannot be copied."
        ty: Type

        @dataclass(frozen=True)
        class Explanation(Note):
            message: ClassVar[str] = "Only arrays with copyable elements can be copied"

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        # First, check if we're trying to copy a non-copyable element type to give a
        # nicer error message. Then, do the full `synthesize_call` type check
        if len(args) == 1:
            args[0], array_ty = ExprSynthesizer(self.ctx).synthesize(args[0])
            if is_array_type(array_ty):
                elem_ty = get_element_type(array_ty)
                if not elem_ty.copyable:
                    err = ArrayCopyChecker.NonCopyableElementsError(self.node, elem_ty)
                    err.add_sub_diagnostic(
                        ArrayCopyChecker.NonCopyableElementsError.Explanation(None)
                    )
                    raise GuppyTypeError(err)
        [array_arg], _, inst = synthesize_call(self.func.ty, args, self.node, self.ctx)
        node = GlobalCall(def_id=self.func.id, args=[array_arg], type_args=inst)
        return with_loc(self.node, node), get_type(array_arg)


class NewArrayChecker(CustomCallChecker):
    """Function call checker for the `array.__new__` function."""

    @dataclass(frozen=True)
    class InferenceError(Error):
        title: ClassVar[str] = "Cannot infer type"
        span_label: ClassVar[str] = "Cannot infer the type of this array"

        @dataclass(frozen=True)
        class Suggestion(Note):
            message: ClassVar[str] = (
                "Consider adding a type annotation: `x: array[???] = ...`"
            )

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        match args:
            case []:
                err = NewArrayChecker.InferenceError(self.node)
                err.add_sub_diagnostic(NewArrayChecker.InferenceError.Suggestion(None))
                raise GuppyTypeError(err)
            # Either an array comprehension
            case [DesugaredGeneratorExpr() as compr]:
                return self.synthesize_array_comprehension(compr)
            # Or a list of array elements
            case [fst, *rest]:
                fst, ty = ExprSynthesizer(self.ctx).synthesize(fst)
                checker = ExprChecker(self.ctx)
                for i in range(len(rest)):
                    rest[i], subst = checker.check(rest[i], ty)
                    assert len(subst) == 0, "Array element type is closed"
                result_ty = array_type(ty, len(args))
                call = GlobalCall(
                    def_id=self.func.id, args=[fst, *rest], type_args=result_ty.args
                )
                return with_loc(self.node, call), result_ty
            case args:
                return assert_never(args)  # type: ignore[arg-type]

    def check(self, args: list[ast.expr], ty: Type) -> tuple[ast.expr, Subst]:
        if not is_array_type(ty):
            dummy_array_ty = array_type_def.check_instantiate(
                [p.to_existential()[0] for p in array_type_def.params],
                self.ctx.globals,
                self.node,
            )
            raise GuppyTypeError(TypeMismatchError(self.node, ty, dummy_array_ty))
        subst: Subst = {}
        match ty.args:
            case [TypeArg(ty=elem_ty), ConstArg(length)]:
                match args:
                    # Either an array comprehension
                    case [DesugaredGeneratorExpr() as compr]:
                        # TODO: We could use the type information to infer some stuff
                        #  in the comprehension
                        arr_compr, res_ty = self.synthesize_array_comprehension(compr)
                        arr_compr = with_loc(self.node, arr_compr)
                        arr_compr, subst, _ = check_type_against(
                            res_ty, ty, arr_compr, self.ctx
                        )
                        return arr_compr, subst
                    # Or a list of array elements
                    case args:
                        checker = ExprChecker(self.ctx)
                        for i in range(len(args)):
                            args[i], s = checker.check(
                                args[i], elem_ty.substitute(subst)
                            )
                            subst |= s
                        ls = unify(length, ConstValue(nat_type(), len(args)), {})
                        if ls is None:
                            raise GuppyTypeError(
                                TypeMismatchError(
                                    self.node, ty, array_type(elem_ty, len(args))
                                )
                            )
                        subst |= ls
                        call = GlobalCall(
                            def_id=self.func.id, args=args, type_args=ty.args
                        )
                        return with_loc(self.node, call), subst
            case type_args:
                raise InternalGuppyError(f"Invalid array type args: {type_args}")

    def synthesize_array_comprehension(
        self, compr: DesugaredGeneratorExpr
    ) -> tuple[DesugaredArrayComp, Type]:
        # Array comprehensions require a static size. To keep things simple, we'll only
        # allow a single generator for now, so we don't have to reason about products
        # of iterator sizes.
        if len(compr.generators) > 1:
            # Individual generator objects unfortunately don't have a span in Python's
            # AST, so we have to use the whole expression span
            raise GuppyError(UnsupportedError(compr, "Nested array comprehensions"))
        [gen] = compr.generators
        # Similarly, dynamic if guards are not allowed
        if gen.ifs:
            err = ArrayComprUnknownSizeError(compr)
            err.add_sub_diagnostic(ArrayComprUnknownSizeError.IfGuard(gen.ifs[0]))
            raise GuppyError(err)
        # Extract the iterator size
        match gen.iter_assign:
            case ast.Assign(value=MakeIter() as make_iter):
                sized_make_iter = MakeIter(
                    make_iter.value, make_iter.origin_node, unwrap_size_hint=False
                )
                _, iter_ty = ExprSynthesizer(self.ctx).synthesize(sized_make_iter)
                # The iterator must have a static size hint
                if not is_sized_iter_type(iter_ty):
                    err = ArrayComprUnknownSizeError(compr)
                    err.add_sub_diagnostic(
                        ArrayComprUnknownSizeError.DynamicIterator(make_iter)
                    )
                    raise GuppyError(err)
                size = get_iter_size(iter_ty)
            case _:
                raise InternalGuppyError("Invalid iterator assign statement")
        # Finally, type check the comprehension
        [gen], elt, elt_ty = synthesize_comprehension(compr, [gen], compr.elt, self.ctx)
        array_compr = DesugaredArrayComp(
            elt=elt, generator=gen, length=size, elt_ty=elt_ty
        )
        return with_loc(compr, array_compr), array_type(elt_ty, size)


#: Maximum length of a tag in the `result` function.
TAG_MAX_LEN = 200


class ResultChecker(CustomCallChecker):
    """Call checker for the `result` function."""

    @dataclass(frozen=True)
    class InvalidError(Error):
        title: ClassVar[str] = "Invalid Result"
        span_label: ClassVar[str] = "Expression of type `{ty}` is not a valid result."
        ty: Type

        @dataclass(frozen=True)
        class Explanation(Note):
            message: ClassVar[str] = (
                "Only numeric values or arrays thereof are allowed as results"
            )

    @dataclass(frozen=True)
    class TooLongError(Error):
        title: ClassVar[str] = "Tag too long"
        span_label: ClassVar[str] = "Result tag is too long"

        @dataclass(frozen=True)
        class Hint(Note):
            message: ClassVar[str] = f"Result tags are limited to {TAG_MAX_LEN} bytes"

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        check_num_args(2, len(args), self.node)
        [tag, value] = args
        tag, _ = ExprChecker(self.ctx).check(tag, string_type())
        if not isinstance(tag, ast.Constant) or not isinstance(tag.value, str):
            raise GuppyTypeError(ExpectedError(tag, "a string literal"))
        if len(tag.value.encode("utf-8")) > TAG_MAX_LEN:
            err: Error = ResultChecker.TooLongError(tag)
            err.add_sub_diagnostic(ResultChecker.TooLongError.Hint(None))
            raise GuppyTypeError(err)
        value, ty = ExprSynthesizer(self.ctx).synthesize(value)
        # We only allow numeric values or vectors of numeric values
        err = ResultChecker.InvalidError(value, ty)
        err.add_sub_diagnostic(ResultChecker.InvalidError.Explanation(None))
        if self._is_numeric_or_bool_type(ty):
            base_ty = ty
            array_len: Const | None = None
        elif is_array_type(ty):
            [ty_arg, len_arg] = ty.args
            assert isinstance(ty_arg, TypeArg)
            assert isinstance(len_arg, ConstArg)
            if not self._is_numeric_or_bool_type(ty_arg.ty):
                raise GuppyError(err)
            base_ty = ty_arg.ty
            array_len = len_arg.const
        else:
            raise GuppyError(err)
        node = ResultExpr(value, base_ty, array_len, tag.value)
        return with_loc(self.node, node), NoneType()

    def check(self, args: list[ast.expr], ty: Type) -> tuple[ast.expr, Subst]:
        expr, res_ty = self.synthesize(args)
        expr, subst, _ = check_type_against(res_ty, ty, expr, self.ctx)
        return expr, subst

    @staticmethod
    def _is_numeric_or_bool_type(ty: Type) -> bool:
        return isinstance(ty, NumericType) or is_bool_type(ty)


class PanicChecker(CustomCallChecker):
    """Call checker for the `panic`  function."""

    @dataclass(frozen=True)
    class NoMessageError(Error):
        title: ClassVar[str] = "No panic message"
        span_label: ClassVar[str] = "Missing message argument to panic call"

        @dataclass(frozen=True)
        class Suggestion(Note):
            message: ClassVar[str] = 'Add a message: `panic("message")`'

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        match args:
            case []:
                err = PanicChecker.NoMessageError(self.node)
                err.add_sub_diagnostic(PanicChecker.NoMessageError.Suggestion(None))
                raise GuppyTypeError(err)
            case [msg, *rest]:
                msg, _ = ExprChecker(self.ctx).check(msg, string_type())
                if not isinstance(msg, ast.Constant) or not isinstance(msg.value, str):
                    raise GuppyTypeError(ExpectedError(msg, "a string literal"))

                vals = [ExprSynthesizer(self.ctx).synthesize(val)[0] for val in rest]
                # TODO variable signals once default arguments are available
                node = PanicExpr(
                    kind=ExitKind.Panic, msg=msg.value, values=vals, signal=1
                )
                return with_loc(self.node, node), NoneType()
            case args:
                return assert_never(args)  # type: ignore[arg-type]

    def check(self, args: list[ast.expr], ty: Type) -> tuple[ast.expr, Subst]:
        # Panic may return any type, so we don't have to check anything. Consequently
        # we also can't infer anything in the expected type, so we always return an
        # empty substitution
        expr, _ = self.synthesize(args)
        return expr, {}


class ExitChecker(CustomCallChecker):
    """Call checker for the ``exit` functions."""

    @dataclass(frozen=True)
    class NoMessageError(Error):
        title: ClassVar[str] = "No exit message"
        span_label: ClassVar[str] = "Missing message argument to exit call"

        @dataclass(frozen=True)
        class Suggestion(Note):
            message: ClassVar[str] = 'Add a message: `exit("message", 0)`'

    @dataclass(frozen=True)
    class NoSignalError(Error):
        title: ClassVar[str] = "No exit signal"
        span_label: ClassVar[str] = "Missing signal argument to exit call"

        @dataclass(frozen=True)
        class Suggestion(Note):
            message: ClassVar[str] = 'Add a signal: `exit("message", 0)`'

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        match args:
            case []:
                msg_err = ExitChecker.NoMessageError(self.node)
                msg_err.add_sub_diagnostic(ExitChecker.NoMessageError.Suggestion(None))
                raise GuppyTypeError(msg_err)
            case [_msg]:
                signal_err = ExitChecker.NoSignalError(self.node)
                signal_err.add_sub_diagnostic(
                    ExitChecker.NoSignalError.Suggestion(None)
                )
                raise GuppyTypeError(signal_err)
            case [msg, signal, *rest]:
                msg, _ = ExprChecker(self.ctx).check(msg, string_type())
                if not isinstance(msg, ast.Constant) or not isinstance(msg.value, str):
                    raise GuppyTypeError(ExpectedError(msg, "a string literal"))
                # TODO allow variable signals after https://github.com/CQCL/hugr/issues/1863
                signal, _ = ExprChecker(self.ctx).check(signal, int_type())
                if not isinstance(signal, ast.Constant) or not isinstance(
                    signal.value, int
                ):
                    raise GuppyTypeError(ExpectedError(msg, "an integer literal"))

                vals = [ExprSynthesizer(self.ctx).synthesize(val)[0] for val in rest]
                node = PanicExpr(
                    kind=ExitKind.ExitShot,
                    msg=msg.value,
                    values=vals,
                    signal=signal.value,
                )
                return with_loc(self.node, node), NoneType()
            case args:
                return assert_never(args)  # type: ignore[arg-type]

    def check(self, args: list[ast.expr], ty: Type) -> tuple[ast.expr, Subst]:
        # Exit may return any type, so we don't have to check anything. Consequently
        # we also can't infer anything in the expected type, so we always return an
        # empty substitution
        expr, _ = self.synthesize(args)
        return expr, {}


class RangeChecker(CustomCallChecker):
    """Call checker for the `range` function."""

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        check_num_args(1, len(args), self.node)
        [stop] = args
        stop_checked, _ = ExprChecker(self.ctx).check(stop, int_type(), "argument")
        range_iter, range_ty = self.make_range(stop_checked)
        # Check if `stop` is a statically known value. Note that we need to do this on
        # the original `stop` instead of `stop_checked` to avoid any previously inserted
        # `int` coercions.
        if (static_stop := self.check_static(stop)) is not None:
            return to_sized_iter(range_iter, range_ty, static_stop, self.ctx)
        return range_iter, range_ty

    def check_static(self, stop: ast.expr) -> "int | Const | None":
        stop, _ = ExprSynthesizer(self.ctx).synthesize(stop, allow_free_vars=True)
        if isinstance(stop, ast.Constant) and isinstance(stop.value, int):
            return stop.value
        if isinstance(stop, GenericParamValue) and stop.param.ty == nat_type():
            return stop.param.to_bound().const
        return None

    def range_ty(self) -> StructType:
        from guppylang.std.builtins import Range

        def_id = cast(RawStructDef, Range).id
        range_type_def = self.ctx.globals.defs[def_id]
        assert isinstance(range_type_def, CheckedStructDef)
        return StructType([], range_type_def)

    def make_range(self, stop: ast.expr) -> tuple[ast.expr, Type]:
        make_range = self.ctx.globals.get_instance_func(self.range_ty(), "__new__")
        assert make_range is not None
        start = with_type(int_type(), with_loc(self.node, ast.Constant(value=0)))
        return make_range.synthesize_call([start, stop], self.node, self.ctx)


def to_sized_iter(
    iterator: ast.expr, range_ty: Type, size: "int | Const", ctx: Context
) -> tuple[ast.expr, Type]:
    """Adds a static size annotation to an iterator."""
    sized_iter_ty = sized_iter_type(range_ty, size)
    make_sized_iter = ctx.globals.get_instance_func(sized_iter_ty, "__new__")
    assert make_sized_iter is not None
    sized_iter, _ = make_sized_iter.check_call([iterator], sized_iter_ty, iterator, ctx)
    return sized_iter, sized_iter_ty


class BarrierChecker(CustomCallChecker):
    """Call checker for the `barrier` function."""

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        tys = [ExprSynthesizer(self.ctx).synthesize(val)[1] for val in args]
        func_ty = FunctionType(
            [FuncInput(t, InputFlags.Inout) for t in tys],
            NoneType(),
        )
        args, ret_ty, inst = synthesize_call(func_ty, args, self.node, self.ctx)
        assert len(inst) == 0, "func_ty is not generic"
        node = BarrierExpr(args=args, func_ty=func_ty)
        return with_loc(self.node, node), ret_ty
