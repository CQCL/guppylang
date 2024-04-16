import ast
from typing import Any, Literal

from pydantic import BaseModel

from guppylang.ast_util import AstNode, get_type, with_loc, with_type
from guppylang.checker.core import Context
from guppylang.checker.expr_checker import ExprSynthesizer, check_num_args
from guppylang.definition.custom import (
    CustomCallChecker,
    CustomCallCompiler,
    CustomFunctionDef,
    DefaultCallChecker,
)
from guppylang.definition.ty import TypeDef
from guppylang.definition.value import CallableDef
from guppylang.error import GuppyError, GuppyTypeError
from guppylang.hugr import ops, tys, val
from guppylang.hugr.hugr import OutPortV
from guppylang.nodes import GlobalCall
from guppylang.tys.builtin import bool_type
from guppylang.tys.subst import Subst
from guppylang.tys.ty import FunctionType, OpaqueType, Type, unify

INT_WIDTH = 6  # 2^6 = 64 bit


hugr_int_type = tys.Opaque(
    extension="arithmetic.int.types",
    id="int",
    args=[tys.BoundedNatArg(n=INT_WIDTH)],
    bound=tys.TypeBound.Eq,
)


hugr_float_type = tys.Opaque(
    extension="arithmetic.float.types",
    id="float64",
    args=[],
    bound=tys.TypeBound.Copyable,
)


class ConstIntS(BaseModel):
    """Hugr representation of signed integers in the arithmetic extension."""

    c: Literal["ConstIntS"] = "ConstIntS"
    log_width: int
    value: int


class ConstF64(BaseModel):
    """Hugr representation of floats in the arithmetic extension."""

    c: Literal["ConstF64"] = "ConstF64"
    value: float


class ListValue(BaseModel):
    """Hugr representation of floats in the arithmetic extension."""

    c: Literal["ListValue"] = "ListValue"
    value: tuple[list[Any], tys.Type]


def bool_value(b: bool) -> val.Value:
    """Returns the Hugr representation of a boolean value."""
    return val.Sum(tag=int(b), value=val.Tuple(vs=[]))


def int_value(i: int) -> val.Value:
    """Returns the Hugr representation of an integer value."""
    return val.ExtensionVal(c=(ConstIntS(log_width=INT_WIDTH, value=i),))


def float_value(f: float) -> val.Value:
    """Returns the Hugr representation of a float value."""
    return val.ExtensionVal(c=(ConstF64(value=f),))


def list_value(v: list[val.Value], ty: tys.Type) -> val.Value:
    """Returns the Hugr representation of a list value."""
    return val.ExtensionVal(c=(ListValue(value=(v, ty)),))


def logic_op(op_name: str, args: list[tys.TypeArg] | None = None) -> ops.OpType:
    """Utility method to create Hugr logic ops."""
    return ops.CustomOp(extension="logic", op_name=op_name, args=args or [])


def int_op(
    op_name: str, ext: str = "arithmetic.int", num_params: int = 1
) -> ops.OpType:
    """Utility method to create Hugr integer arithmetic ops."""
    return ops.CustomOp(
        extension=ext,
        op_name=op_name,
        args=num_params * [tys.BoundedNatArg(n=INT_WIDTH)],
    )


def float_op(op_name: str, ext: str = "arithmetic.float") -> ops.OpType:
    """Utility method to create Hugr integer arithmetic ops."""
    return ops.CustomOp(extension=ext, op_name=op_name, args=[])


class CoercingChecker(DefaultCallChecker):
    """Function call type checker that automatically coerces arguments to float."""

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        from .builtins import Int

        for i in range(len(args)):
            args[i], ty = ExprSynthesizer(self.ctx).synthesize(args[i])
            if isinstance(ty, OpaqueType) and ty.defn == self.ctx.globals["int"]:
                call = with_loc(
                    self.node,
                    GlobalCall(def_id=Int.__float__.id, args=[args[i]], type_args=[]),
                )
                float_defn = self.ctx.globals["float"]
                assert isinstance(float_defn, TypeDef)
                args[i] = with_type(float_defn.check_instantiate([]), call)
        return super().synthesize(args)


class ReversingChecker(CustomCallChecker):
    """Call checker that reverses the arguments after checking."""

    base_checker: CustomCallChecker

    def __init__(self, base_checker: CustomCallChecker | None = None):
        self.base_checker = base_checker or DefaultCallChecker()

    def _setup(self, ctx: Context, node: AstNode, func: CustomFunctionDef) -> None:
        super()._setup(ctx, node, func)
        self.base_checker._setup(ctx, node, func)

    def check(self, args: list[ast.expr], ty: Type) -> tuple[ast.expr, Subst]:
        expr, subst = self.base_checker.check(args, ty)
        if isinstance(expr, GlobalCall):
            expr.args = list(reversed(args))
        return expr, subst

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        expr, ty = self.base_checker.synthesize(args)
        if isinstance(expr, GlobalCall):
            expr.args = list(reversed(args))
        return expr, ty


class FailingChecker(CustomCallChecker):
    """Call checker for Python functions that are not available in Guppy.

    Gives the uses a nicer error message when they try to use an unsupported feature.
    """

    def __init__(self, msg: str) -> None:
        self.msg = msg

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        raise GuppyError(self.msg, self.node)

    def check(self, args: list[ast.expr], ty: Type) -> tuple[ast.expr, Subst]:
        raise GuppyError(self.msg, self.node)


class UnsupportedChecker(CustomCallChecker):
    """Call checker for Python builtin functions that are not available in Guppy.

    Gives the uses a nicer error message when they try to use an unsupported feature.
    """

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        raise GuppyError(
            f"Builtin method `{self.func.name}` is not supported by Guppy", self.node
        )

    def check(self, args: list[ast.expr], ty: Type) -> tuple[ast.expr, Subst]:
        raise GuppyError(
            f"Builtin method `{self.func.name}` is not supported by Guppy", self.node
        )


class DunderChecker(CustomCallChecker):
    """Call checker for builtin functions that call out to dunder instance methods"""

    dunder_name: str
    num_args: int

    def __init__(self, dunder_name: str, num_args: int = 1):
        assert num_args > 0
        self.dunder_name = dunder_name
        self.num_args = num_args

    def _get_func(self, args: list[ast.expr]) -> tuple[list[ast.expr], CallableDef]:
        check_num_args(self.num_args, len(args), self.node)
        fst, *rest = args
        fst, ty = ExprSynthesizer(self.ctx).synthesize(fst)
        func = self.ctx.globals.get_instance_func(ty, self.dunder_name)
        if func is None:
            raise GuppyTypeError(
                f"Builtin function `{self.func.name}` is not defined for argument of "
                f"type `{ty}`",
                self.node.args[0] if isinstance(self.node, ast.Call) else self.node,
            )
        return [fst, *rest], func

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        args, func = self._get_func(args)
        return func.synthesize_call(args, self.node, self.ctx)

    def check(self, args: list[ast.expr], ty: Type) -> tuple[ast.expr, Subst]:
        args, func = self._get_func(args)
        return func.check_call(args, ty, self.node, self.ctx)


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

    def check(self, args: list[ast.expr], ty: Type) -> tuple[ast.expr, Subst]:
        args, _ = self.synthesize(args)
        subst = unify(ty, bool_type(), {})
        if subst is None:
            raise GuppyTypeError(
                f"Expected expression of type `{ty}`, got `bool`", self.node
            )
        return args, subst


class IntTruedivCompiler(CustomCallCompiler):
    """Compiler for the `int.__truediv__` method."""

    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        from .builtins import Float, Int

        # Compile `truediv` using float arithmetic
        [left, right] = args
        [left] = Int.__float__.compile_call(
            [left], [], self.dfg, self.graph, self.globals, self.node
        )
        [right] = Int.__float__.compile_call(
            [right], [], self.dfg, self.graph, self.globals, self.node
        )
        [out] = Float.__truediv__.compile_call(
            [left, right], [], self.dfg, self.graph, self.globals, self.node
        )
        return [out]


class FloatBoolCompiler(CustomCallCompiler):
    """Compiler for the `float.__bool__` method."""

    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        from .builtins import Float

        # We have: bool(x) = (x != 0.0)
        zero_const = self.graph.add_constant(
            float_value(0.0), get_type(self.node), self.dfg.node
        )
        zero = self.graph.add_load_constant(zero_const.out_port(0), self.dfg.node)
        [out] = Float.__ne__.compile_call(
            [args[0], zero.out_port(0)],
            [],
            self.dfg,
            self.graph,
            self.globals,
            self.node,
        )
        return [out]


class FloatFloordivCompiler(CustomCallCompiler):
    """Compiler for the `float.__floordiv__` method."""

    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        from .builtins import Float

        # We have: floordiv(x, y) = floor(truediv(x, y))
        [div] = Float.__truediv__.compile_call(
            args, [], self.dfg, self.graph, self.globals, self.node
        )
        [floor] = Float.__floor__.compile_call(
            [div], [], self.dfg, self.graph, self.globals, self.node
        )
        return [floor]


class FloatModCompiler(CustomCallCompiler):
    """Compiler for the `float.__mod__` method."""

    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        from .builtins import Float

        # We have: mod(x, y) = x - (x // y) * y
        [div] = Float.__floordiv__.compile_call(
            args, [], self.dfg, self.graph, self.globals, self.node
        )
        [mul] = Float.__mul__.compile_call(
            [div, args[1]], [], self.dfg, self.graph, self.globals, self.node
        )
        [sub] = Float.__sub__.compile_call(
            [args[0], mul], [], self.dfg, self.graph, self.globals, self.node
        )
        return [sub]


class FloatDivmodCompiler(CustomCallCompiler):
    """Compiler for the `__divmod__` method."""

    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        from .builtins import Float

        # We have: divmod(x, y) = (div(x, y), mod(x, y))
        [div] = Float.__truediv__.compile_call(
            args, [], self.dfg, self.graph, self.globals, self.node
        )
        [mod] = Float.__mod__.compile_call(
            args, [], self.dfg, self.graph, self.globals, self.node
        )
        return [self.graph.add_make_tuple([div, mod], self.dfg.node).out_port(0)]


class MeasureCompiler(CustomCallCompiler):
    """Compiler for the `measure` function."""

    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        from .quantum import quantum_op

        [qubit] = args
        measure = self.graph.add_node(quantum_op("Measure"), inputs=args)
        self.graph.add_node(
            quantum_op("QFree"), inputs=[measure.add_out_port(qubit.ty)]
        )
        return [measure.add_out_port(bool_type())]
