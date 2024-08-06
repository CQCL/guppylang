import ast

from guppylang.ast_util import AstNode, with_loc
from guppylang.checker.core import Context
from guppylang.checker.expr_checker import (
    ExprSynthesizer,
    check_call,
    check_num_args,
    check_type_against,
    synthesize_call,
)
from guppylang.definition.custom import (
    CustomCallChecker,
    CustomFunctionDef,
    DefaultCallChecker,
)
from guppylang.definition.value import CallableDef
from guppylang.error import GuppyError, GuppyTypeError, InternalGuppyError
from guppylang.nodes import GlobalCall, ResultExpr
from guppylang.tys.arg import ConstArg
from guppylang.tys.builtin import bool_type, int_type
from guppylang.tys.const import ConstValue
from guppylang.tys.subst import Inst, Subst
from guppylang.tys.ty import (
    FunctionType,
    NoneType,
    NumericType,
    Type,
    unify,
)


class CoercingChecker(DefaultCallChecker):
    """Function call type checker that automatically coerces arguments to float."""

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        for i in range(len(args)):
            args[i], ty = ExprSynthesizer(self.ctx).synthesize(args[i])
            if isinstance(ty, NumericType) and ty.kind != NumericType.Kind.Float:
                to_float = self.ctx.globals.get_instance_func(ty, "__float__")
                assert to_float is not None
                args[i], _ = to_float.synthesize_call([args[i]], self.node, self.ctx)
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


class ArrayLenChecker(CustomCallChecker):
    """Function call checker for the `array.__len__` function."""

    @staticmethod
    def _get_const_len(inst: Inst) -> ast.expr:
        """Helper function to extract the static length from the inferred type args."""
        # TODO: This will stop working once we allow generic function defs. Then, the
        #  argument could also just be variable instead of a concrete number.
        match inst:
            case [_, ConstArg(const=ConstValue(value=int(n)))]:
                return ast.Constant(value=n)
        raise InternalGuppyError(f"array.__len__: Invalid instantiation: {inst}")

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        _, _, inst = synthesize_call(self.func.ty, args, self.node, self.ctx)
        return self._get_const_len(inst), int_type()

    def check(self, args: list[ast.expr], ty: Type) -> tuple[ast.expr, Subst]:
        _, subst, inst = check_call(self.func.ty, args, ty, self.node, self.ctx)
        return self._get_const_len(inst), subst


class ResultChecker(CustomCallChecker):
    """Call checker for the `result` function.

    This is a temporary hack until we have implemented the proper results mechanism.
    """

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        check_num_args(2, len(args), self.node)
        [tag, value] = args
        if not isinstance(tag, ast.Constant) or not isinstance(tag.value, int):
            raise GuppyTypeError("Expected an int literal", tag)
        value, ty = ExprSynthesizer(self.ctx).synthesize(value)
        if ty.linear:
            raise GuppyTypeError(
                f"Cannot use value with linear type `{ty}` as a result", value
            )
        return with_loc(self.node, ResultExpr(value, ty, tag.value)), NoneType()

    def check(self, args: list[ast.expr], ty: Type) -> tuple[ast.expr, Subst]:
        expr, res_ty = self.synthesize(args)
        subst, _ = check_type_against(res_ty, ty, self.node)
        return expr, subst
