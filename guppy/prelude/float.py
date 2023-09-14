"""Guppy standard extension for float operations."""

# mypy: disable-error-code=empty-body

from guppy.prelude import builtin
from guppy.prelude.builtin import IntType, FloatType, float_value
from guppy.compiler_base import CallCompiler
from guppy.extension import (
    GuppyExtension,
    OpCompiler,
    Reversed,
    NotImplementedCompiler,
    NoopCompiler,
)
from guppy.hugr import ops
from guppy.hugr.hugr import OutPortV


class FloatOpCompiler(OpCompiler):
    """Compiler for calls that can be implemented via a single Hugr float op"""

    def __init__(self, op_name: str, extension: str = "arithmetic.float"):
        super().__init__(ops.CustomOp(extension=extension, op_name=op_name, args=[]))

    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        args = [
            self.graph.add_node(
                ops.CustomOp(extension="arithmetic.conversions", op_name="convert_s"),
                inputs=[arg],
                parent=self.parent,
            ).add_out_port(FloatType())
            if isinstance(arg.ty, IntType)
            else arg
            for arg in args
        ]
        return super().compile(args)


class BoolCompiler(CallCompiler):
    """Compiler for the `__bool__` method."""

    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        # We have: bool(x) = (x != 0.0)
        zero_const = self.graph.add_constant(float_value(0.0), FloatType(), self.parent)
        zero = self.graph.add_load_constant(zero_const.out_port(0), self.parent)
        return __ne__.compile_call(
            [args[0], zero.out_port(0)], self.dfg, self.graph, self.globals, self.node
        )


class FloordivCompiler(CallCompiler):
    """Compiler for the `__floordiv__` method."""

    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        # We have: floordiv(x, y) = floor(truediv(x, y))
        [div] = __truediv__.compile_call(
            args, self.dfg, self.graph, self.globals, self.node
        )
        [floor] = __floor__.compile_call(
            [div], self.dfg, self.graph, self.globals, self.node
        )
        return [floor]


class ModCompiler(CallCompiler):
    """Compiler for the `__mod__` method."""

    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        # We have: mod(x, y) = x - (x // y) * y
        [div] = __floordiv__.compile_call(
            args, self.dfg, self.graph, self.globals, self.node
        )
        [mul] = __mul__.compile_call(
            [div, args[1]], self.dfg, self.graph, self.globals, self.node
        )
        [sub] = __sub__.compile_call(
            [args[0], mul], self.dfg, self.graph, self.globals, self.node
        )
        return [sub]


class DivmodCompiler(CallCompiler):
    """Compiler for the `__divmod__` method."""

    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        # We have: divmod(x, y) = (div(x, y), mod(x, y))
        [div] = __truediv__.compile_call(
            args, self.dfg, self.graph, self.globals, self.node
        )
        [mod] = __mod__.compile_call(
            args, self.dfg, self.graph, self.globals, self.node
        )
        return [self.graph.add_make_tuple([div, mod], self.parent).out_port(0)]


extension = GuppyExtension("float", [builtin])


@extension.func(FloatOpCompiler("fabs"), instance=FloatType)
def __abs__(self: float) -> float:
    ...


@extension.func(FloatOpCompiler("fadd"), instance=FloatType)
def __add__(self: float, other: float) -> float:
    ...


@extension.func(BoolCompiler(), instance=FloatType)
def __bool__(self: int) -> bool:
    ...


@extension.func(FloatOpCompiler("fceil"), instance=FloatType)
def __ceil__(self: float) -> float:
    ...


@extension.func(DivmodCompiler(), instance=FloatType)
def __divmod__(self: float, other: float) -> tuple[float, float]:
    ...


@extension.func(FloatOpCompiler("feq"), instance=FloatType)
def __eq__(self: float, other: float) -> bool:
    ...


@extension.func(NoopCompiler(), instance=FloatType)
def __float__(self: float) -> float:
    ...


@extension.func(FloatOpCompiler("ffloor"), instance=FloatType)
def __floor__(self: float) -> float:
    ...


@extension.func(FloordivCompiler(), instance=FloatType)
def __floordiv__(self: float, other: float) -> float:
    ...


@extension.func(FloatOpCompiler("fge"), instance=FloatType)
def __ge__(self: float, other: float) -> bool:
    ...


@extension.func(FloatOpCompiler("fgt"), instance=FloatType)
def __gt__(self: float, other: float) -> bool:
    ...


@extension.func(
    FloatOpCompiler("trunc_s", "arithmetic.conversions"), instance=FloatType
)
def __int__(self: float, other: float) -> int:
    ...


@extension.func(FloatOpCompiler("fle"), instance=FloatType)
def __le__(self: float, other: float) -> bool:
    ...


@extension.func(FloatOpCompiler("flt"), instance=FloatType)
def __lt__(self: float, other: float) -> bool:
    ...


@extension.func(ModCompiler(), instance=FloatType)
def __mod__(self: float, other: float) -> float:
    ...


@extension.func(FloatOpCompiler("fmul"), instance=FloatType)
def __mul__(self: float, other: float) -> float:
    ...


@extension.func(FloatOpCompiler("fne"), instance=FloatType)
def __ne__(self: float, other: float) -> bool:
    ...


@extension.func(FloatOpCompiler("fneg"), instance=FloatType)
def __neg__(self: float, other: float) -> float:
    ...


@extension.func(NoopCompiler(), instance=FloatType)
def __pos__(self: int) -> int:
    ...


@extension.func(NotImplementedCompiler(), instance=FloatType)  # TODO
def __pow__(self: float, other: float) -> float:
    ...


@extension.func(Reversed(FloatOpCompiler("fadd")), instance=FloatType)
def __radd__(self: float, other: float) -> float:
    ...


@extension.func(Reversed(DivmodCompiler()), instance=FloatType)
def __rdivmod__(self: float, other: float) -> float:
    ...


@extension.func(Reversed(ModCompiler()), instance=FloatType)
def __rmod__(self: float, other: float) -> float:
    ...


@extension.func(Reversed(FloatOpCompiler("fmul")), instance=FloatType)
def __rmul__(self: float, other: float) -> float:
    ...


@extension.func(NotImplementedCompiler(), instance=FloatType)  # TODO
def __round__(self: float) -> float:
    ...


@extension.func(Reversed(NotImplementedCompiler()), instance=FloatType)  # TODO
def __rpow__(self: float, other: float) -> float:
    ...


@extension.func(Reversed(FloatOpCompiler("fsub")), instance=FloatType)
def __rsub__(self: float, other: float) -> int:
    ...


@extension.func(FloatOpCompiler("fdiv"), instance=FloatType)
def __rtruediv__(self: float, other: float) -> float:
    ...


@extension.func(NotImplementedCompiler(), instance=FloatType)  # TODO
def __str__(self: int) -> str:
    ...


@extension.func(FloatOpCompiler("fsub"), instance=FloatType)
def __sub__(self: float, other: float) -> int:
    ...


@extension.func(FloatOpCompiler("fdiv"), instance=FloatType)
def __truediv__(self: float, other: float) -> float:
    ...


@extension.func(
    FloatOpCompiler("trunc_s", "arithmetic.conversions"), instance=FloatType
)
def __trunc__(self: float, other: float) -> int:
    ...
