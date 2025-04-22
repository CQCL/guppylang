import ast
from dataclasses import dataclass
from typing import ClassVar

from guppylang.ast_util import with_loc
from guppylang.checker.errors.generic import ExpectedError
from guppylang.checker.errors.type_errors import WrongNumberOfArgsError
from guppylang.checker.expr_checker import ExprChecker, ExprSynthesizer, synthesize_call
from guppylang.definition.custom import CustomCallChecker
from guppylang.definition.ty import TypeDef
from guppylang.diagnostic import Error
from guppylang.error import GuppyTypeError
from guppylang.nodes import StateResultExpr
from guppylang.std._internal.checker import TAG_MAX_LEN, TooLongError
from guppylang.tys.builtin import (
    get_array_length,
    get_element_type,
    is_array_type,
    string_type,
)
from guppylang.tys.ty import FuncInput, FunctionType, InputFlags, NoneType, Type


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

        from guppylang.std.quantum import qubit

        qubit_defn = self.ctx.globals[qubit.id]
        assert isinstance(qubit_defn, TypeDef)
        qubit_ty = qubit_defn.check_instantiate([], self.ctx.globals)

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
