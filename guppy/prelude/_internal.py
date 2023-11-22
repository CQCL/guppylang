import ast
from typing import Optional, Literal

from pydantic import BaseModel

from guppy.ast_util import with_type, AstNode, with_loc, get_type
from guppy.checker.core import Context, CallableVariable
from guppy.checker.expr_checker import ExprSynthesizer, check_num_args
from guppy.custom import (
    CustomCallChecker,
    DefaultCallChecker,
    CustomFunction,
    CustomCallCompiler,
)
from guppy.error import GuppyTypeError, GuppyError
from guppy.types import GuppyType, type_to_row, FunctionType, BoolType
from guppy.hugr import ops, tys, val
from guppy.hugr.hugr import OutPortV
from guppy.nodes import GlobalCall


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


def bool_value(b: bool) -> val.Value:
    """Returns the Hugr representation of a boolean value."""
    return val.Sum(tag=int(b), value=val.Tuple(vs=[]))


def int_value(i: int) -> val.Value:
    """Returns the Hugr representation of an integer value."""
    return val.Prim(val=val.ExtensionVal(c=(ConstIntS(log_width=INT_WIDTH, value=i),)))


def float_value(f: float) -> val.Value:
    """Returns the Hugr representation of a float value."""
    return val.Prim(val=val.ExtensionVal(c=(ConstF64(value=f),)))


def logic_op(op_name: str, args: Optional[list[tys.TypeArgUnion]] = None) -> ops.OpType:
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
    """Function call type checker thag automatically coerces arguments to float."""

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, GuppyType]:
        from .builtins import Int

        for i in range(len(args)):
            args[i], ty = ExprSynthesizer(self.ctx).synthesize(args[i])
            if isinstance(ty, self.ctx.globals.types["int"]):
                call = with_loc(
                    self.node, GlobalCall(func=Int.__float__, args=[args[i]])
                )
                args[i] = with_type(self.ctx.globals.types["float"].build(), call)
        return super().synthesize(args)


class ReversingChecker(CustomCallChecker):
    """Call checker that reverses the arguments after checking."""

    base_checker: CustomCallChecker

    def __init__(self, base_checker: CustomCallChecker):
        self.base_checker = base_checker

    def _setup(self, ctx: Context, node: AstNode, func: CustomFunction) -> None:
        super()._setup(ctx, node, func)
        self.base_checker._setup(ctx, node, func)

    def check(self, args: list[ast.expr], ty: GuppyType) -> ast.expr:
        expr = self.base_checker.check(args, ty)
        if isinstance(expr, GlobalCall):
            expr.args = list(reversed(args))
        return expr

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, GuppyType]:
        expr, ty = self.base_checker.synthesize(args)
        if isinstance(expr, GlobalCall):
            expr.args = list(reversed(args))
        return expr, ty


class DunderChecker(CustomCallChecker):
    """Call checker for builtin functions that call out to dunder instance methods"""

    dunder_name: str
    num_args: int

    def __init__(self, dunder_name: str, num_args: int = 1):
        assert num_args > 0
        self.dunder_name = dunder_name
        self.num_args = num_args

    def _get_func(
        self, args: list[ast.expr]
    ) -> tuple[list[ast.expr], CallableVariable]:
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

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, GuppyType]:
        args, func = self._get_func(args)
        return func.synthesize_call(args, self.node, self.ctx)

    def check(self, args: list[ast.expr], ty: GuppyType) -> ast.expr:
        args, func = self._get_func(args)
        return func.check_call(args, ty, self.node, self.ctx)


class CallableChecker(CustomCallChecker):
    """Call checker for the builtin `callable` function"""

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, GuppyType]:
        check_num_args(1, len(args), self.node)
        [arg] = args
        arg, ty = ExprSynthesizer(self.ctx).synthesize(arg)
        is_callable = (
            isinstance(ty, FunctionType)
            or self.ctx.globals.get_instance_func(ty, "__call__") is not None
        )
        const = with_loc(self.node, ast.Constant(value=is_callable))
        return const, BoolType()


class IntTruedivCompiler(CustomCallCompiler):
    """Compiler for the `int.__truediv__` method."""

    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        from .builtins import Int, Float

        # Compile `truediv` using float arithmetic
        [left, right] = args
        [left] = Int.__float__.compile_call(
            [left], self.dfg, self.graph, self.globals, self.node
        )
        [right] = Int.__float__.compile_call(
            [right], self.dfg, self.graph, self.globals, self.node
        )
        return Float.__truediv__.compile_call(
            [left, right], self.dfg, self.graph, self.globals, self.node
        )


class FloatBoolCompiler(CustomCallCompiler):
    """Compiler for the `float.__bool__` method."""

    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        from .builtins import Float

        # We have: bool(x) = (x != 0.0)
        zero_const = self.graph.add_constant(
            float_value(0.0), get_type(self.node), self.dfg.node
        )
        zero = self.graph.add_load_constant(zero_const.out_port(0), self.dfg.node)
        return Float.__ne__.compile_call(
            [args[0], zero.out_port(0)], self.dfg, self.graph, self.globals, self.node
        )


class FloatFloordivCompiler(CustomCallCompiler):
    """Compiler for the `float.__floordiv__` method."""

    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        from .builtins import Float

        # We have: floordiv(x, y) = floor(truediv(x, y))
        [div] = Float.__truediv__.compile_call(
            args, self.dfg, self.graph, self.globals, self.node
        )
        [floor] = Float.__floor__.compile_call(
            [div], self.dfg, self.graph, self.globals, self.node
        )
        return [floor]


class FloatModCompiler(CustomCallCompiler):
    """Compiler for the `float.__mod__` method."""

    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        from .builtins import Float

        # We have: mod(x, y) = x - (x // y) * y
        [div] = Float.__floordiv__.compile_call(
            args, self.dfg, self.graph, self.globals, self.node
        )
        [mul] = Float.__mul__.compile_call(
            [div, args[1]], self.dfg, self.graph, self.globals, self.node
        )
        [sub] = Float.__sub__.compile_call(
            [args[0], mul], self.dfg, self.graph, self.globals, self.node
        )
        return [sub]


class FloatDivmodCompiler(CustomCallCompiler):
    """Compiler for the `__divmod__` method."""

    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        from .builtins import Float

        # We have: divmod(x, y) = (div(x, y), mod(x, y))
        [div] = Float.__truediv__.compile_call(
            args, self.dfg, self.graph, self.globals, self.node
        )
        [mod] = Float.__mod__.compile_call(
            args, self.dfg, self.graph, self.globals, self.node
        )
        return [self.graph.add_make_tuple([div, mod], self.dfg.node).out_port(0)]
