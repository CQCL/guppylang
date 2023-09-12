"""Guppy standard extension for int operations."""

# mypy: disable-error-code=empty-body

from guppy.compiler_base import CallCompiler
from guppy.expression import type_check_call
from guppy.guppy_types import FunctionType
from guppy.hugr.hugr import OutPortV
from guppy.prelude import builtin
from guppy.prelude.builtin import IntType, INT_WIDTH, FloatType
from guppy.extension import (
    GuppyExtension,
    OpCompiler,
    Reversed,
    NotImplementedCompiler,
    NoopCompiler,
)
from guppy.hugr import ops, tys


class IntOpCompiler(OpCompiler):
    def __init__(self, op_name: str, ext: str = "arithmetic.int"):
        super().__init__(
            ops.CustomOp(
                extension=ext, op_name=op_name, args=[tys.BoundedNatArg(n=INT_WIDTH)]
            )
        )


class TruedivCompiler(CallCompiler):
    """Compiler for the `__truediv__` function"""

    signature: FunctionType = FunctionType([IntType(), IntType()], [FloatType()])

    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        # Compile `truediv` using float arithmetic
        import guppy.prelude.float

        type_check_call(self.signature, args, self.node)
        [left, right] = args
        [left] = __float__.compile_call(
            [left], self.parent, self.graph, self.globals, self.node
        )
        [right] = __float__.compile_call(
            [right], self.parent, self.graph, self.globals, self.node
        )
        return guppy.prelude.float.__truediv__.compile_call(
            [left, right], self.parent, self.graph, self.globals, self.node
        )


extension = GuppyExtension("integer", dependencies=[builtin])


@extension.func(
    IntOpCompiler("iabs"), instance=IntType
)  # TODO: Maybe wrong?? (signed vs unsigned!)
def __abs__(self: int) -> int:
    ...


@extension.func(IntOpCompiler("iadd"), instance=IntType)
def __add__(self: int, other: int) -> int:
    ...


@extension.func(IntOpCompiler("iand"), instance=IntType)
def __and__(self: int, other: int) -> int:
    ...


@extension.func(IntOpCompiler("itobool"), instance=IntType)
def __bool__(self: int) -> bool:
    ...


@extension.func(OpCompiler(ops.Noop(ty=IntType().to_hugr())), instance=IntType)
def __ceil__(self: int) -> int:
    ...


@extension.func(IntOpCompiler("idivmod_s"), instance=IntType)
def __divmod__(self: int, other: int) -> tuple[int, int]:
    ...


@extension.func(IntOpCompiler("ieq"), instance=IntType)
def __eq__(self: int, other: int) -> bool:
    ...


@extension.func(IntOpCompiler("convert_s", "arithmetic.conversions"), instance=IntType)
def __float__(self: int) -> float:
    ...


@extension.func(NoopCompiler(), instance=IntType)
def __floor__(self: int, other: int) -> int:
    ...


@extension.func(IntOpCompiler("idiv_s"), instance=IntType)
def __floordiv__(self: int, other: int) -> int:
    ...


@extension.func(IntOpCompiler("ige_s"), instance=IntType)
def __ge__(self: int, other: int) -> bool:
    ...


@extension.func(IntOpCompiler("igt_s"), instance=IntType)
def __gt__(self: int, other: int) -> bool:
    ...


@extension.func(NoopCompiler(), instance=IntType)
def __int__(self: int) -> int:
    ...


@extension.func(IntOpCompiler("inot"), instance=IntType)
def __invert__(self: int) -> int:
    ...


@extension.func(IntOpCompiler("ile_s"), instance=IntType)
def __le__(self: int, other: int) -> bool:
    ...


@extension.func(
    IntOpCompiler("ishl"), instance=IntType
)  # TODO: broken (RHS is unsigned)
def __lshift__(self: int, other: int) -> int:
    ...


@extension.func(IntOpCompiler("ilt_s"), instance=IntType)
def __lt__(self: int, other: int) -> bool:
    ...


@extension.func(IntOpCompiler("imod_s"), instance=IntType)
def __mod__(self: int, other: int) -> int:
    ...


@extension.func(IntOpCompiler("imul"), instance=IntType)
def __mul__(self: int, other: int) -> int:
    ...


@extension.func(IntOpCompiler("ine"), instance=IntType)
def __ne__(self: int, other: int) -> bool:
    ...


@extension.func(IntOpCompiler("ineg"), instance=IntType)
def __neg__(self: int) -> int:
    ...


@extension.func(IntOpCompiler("ior"), instance=IntType)
def __or__(self: int, other: int) -> int:
    ...


@extension.func(NoopCompiler(), instance=IntType)
def __pos__(self: int) -> int:
    ...


@extension.func(NotImplementedCompiler(), instance=IntType)  # TODO
def __pow__(self: int, other: int) -> int:
    ...


@extension.func(Reversed(IntOpCompiler("iadd")), instance=IntType)
def __radd__(self: int, other: int) -> int:
    ...


@extension.func(Reversed(IntOpCompiler("iand")), instance=IntType)
def __rand__(self: int, other: int) -> int:
    ...


@extension.func(Reversed(IntOpCompiler("idivmod_s")), instance=IntType)
def __rdivmod__(self: int, other: int) -> int:
    ...


@extension.func(Reversed(IntOpCompiler("idiv_s")), instance=IntType)
def __rfloordiv__(self: int, other: int) -> int:
    ...


@extension.func(
    Reversed(IntOpCompiler("ishl")), instance=IntType
)  # TODO: broken (RHS is unsigned)
def __rlshift__(self: int, other: int) -> int:
    ...


@extension.func(Reversed(IntOpCompiler("imod_s")), instance=IntType)
def __rmod__(self: int, other: int) -> int:
    ...


@extension.func(Reversed(IntOpCompiler("imul")), instance=IntType)
def __rmul__(self: int, other: int) -> int:
    ...


@extension.func(Reversed(IntOpCompiler("ior")), instance=IntType)
def __ror__(self: int, other: int) -> int:
    ...


@extension.func(NoopCompiler(), instance=IntType)
def __round__(self: int) -> int:
    ...


@extension.func(Reversed(NotImplementedCompiler()), instance=IntType)  # TODO
def __rpow__(self: int, other: int) -> int:
    ...


@extension.func(
    Reversed(IntOpCompiler("ishr")), instance=IntType
)  # TODO: broken (RHS is unsigned)
def __rrshift__(self: int, other: int) -> int:
    ...


@extension.func(
    Reversed(IntOpCompiler("ishr")), instance=IntType
)  # TODO: broken (RHS is unsigned)
def __rshift__(self: int, other: int) -> int:
    ...


@extension.func(
    Reversed(IntOpCompiler("isub")), instance=IntType
)  # TODO: broken (RHS is unsigned)
def __rsub__(self: int, other: int) -> int:
    ...


@extension.func(Reversed(TruedivCompiler()), instance=IntType)
def __rtruediv__(self: int, other: int) -> float:
    ...


@extension.func(Reversed(IntOpCompiler("ixor")), instance=IntType)
def __rxor__(self: int, other: int) -> int:
    ...


@extension.func(NotImplementedCompiler(), instance=IntType)
def __str__(self: int) -> str:
    ...


@extension.func(IntOpCompiler("sub"), instance=IntType)
def __sub__(self: int, other: int) -> int:
    ...


@extension.func(TruedivCompiler(), instance=IntType)
def __truediv__(self: int, other: int) -> float:
    ...


@extension.func(NoopCompiler(), instance=IntType)
def __trunc__(self: int, other: int) -> int:
    ...


@extension.func(IntOpCompiler("ixor"), instance=IntType)
def __xor__(self: int, other: int) -> int:
    ...
