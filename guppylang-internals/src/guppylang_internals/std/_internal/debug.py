import ast
from dataclasses import dataclass
from typing import ClassVar, cast

from guppylang_internals.ast_util import with_loc
from guppylang_internals.checker.errors.generic import ExpectedError
from guppylang_internals.checker.errors.type_errors import WrongNumberOfArgsError
from guppylang_internals.checker.expr_checker import (
    ExprChecker,
    ExprSynthesizer,
    synthesize_call,
)
from guppylang_internals.definition.custom import CustomCallChecker
from guppylang_internals.definition.ty import TypeDef
from guppylang_internals.diagnostic import Error
from guppylang_internals.error import GuppyTypeError
from guppylang_internals.nodes import StateResultExpr
from guppylang_internals.std._internal.checker import TAG_MAX_LEN, TooLongError
from guppylang_internals.tys.builtin import (
    get_array_length,
    get_element_type,
    is_array_type,
    string_type,
)
from guppylang_internals.tys.ty import (
    FuncInput,
    FunctionType,
    InputFlags,
    NoneType,
    Type,
)


class StateResultChecker(CustomCallChecker):
    """Call checker for the `state_result` function."""

    @dataclass(frozen=True)
    class MissingQubitsError(Error):
        title: ClassVar[str] = "Missing qubit inputs"
        span_label: ClassVar[str] = (
            "Qubits whose state should be reported must be passed explicitly"
        )

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        tag, _ = ExprChecker(self.ctx).check(args[0], string_type())
        if not isinstance(tag, ast.Constant) or not isinstance(tag.value, str):
            raise GuppyTypeError(ExpectedError(tag, "a string literal"))
        if len(tag.value.encode("utf-8")) > TAG_MAX_LEN:
            err: Error = TooLongError(tag)
            err.add_sub_diagnostic(TooLongError.Hint(None))
            raise GuppyTypeError(err)
        syn_args: list[ast.expr] = [tag]

        if len(args) < 2:
            raise GuppyTypeError(self.MissingQubitsError(self.node))

        from guppylang.defs import GuppyDefinition
        from guppylang.std.quantum import qubit

        assert isinstance(qubit, GuppyDefinition)
        qubit_ty = cast(TypeDef, qubit.wrapped).check_instantiate([])

        array_len = None
        arg, ty = ExprSynthesizer(self.ctx).synthesize(args[1])
        if is_array_type(ty):
            if len(args) > 2:
                err = WrongNumberOfArgsError(args[2], 2, len(args))
                raise GuppyTypeError(err)
            element_ty = get_element_type(ty)
            if not element_ty == qubit_ty:
                raise GuppyTypeError(ExpectedError(arg, "an array of qubits"))
            syn_args.append(arg)
            func_ty = FunctionType(
                [
                    FuncInput(string_type(), InputFlags.NoFlags),
                    FuncInput(ty, InputFlags.Inout),
                ],
                NoneType(),
            )
            array_len = get_array_length(ty)
        else:
            for arg in args[1:]:
                qbt, _ = ExprChecker(self.ctx).check(arg, qubit_ty)
                syn_args.append(qbt)
            func_ty = FunctionType(
                [FuncInput(string_type(), InputFlags.NoFlags)]
                + [FuncInput(qubit_ty, InputFlags.Inout)] * len(args[1:]),
                NoneType(),
            )
        args, ret_ty, inst = synthesize_call(func_ty, syn_args, self.node, self.ctx)
        assert len(inst) == 0, "func_ty is not generic"
        node = StateResultExpr(
            tag=tag.value, args=args, func_ty=func_ty, array_len=array_len
        )
        return with_loc(self.node, node), ret_ty
