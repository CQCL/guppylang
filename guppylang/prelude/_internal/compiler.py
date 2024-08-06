import hugr
from hugr import Wire, ops

from guppylang.definition.custom import (
    CustomCallCompiler,
)


class NatTruedivCompiler(CustomCallCompiler):
    """Compiler for the `nat.__truediv__` method."""

    def compile(self, args: list[Wire]) -> list[Wire]:
        from guppylang.prelude.builtins import Float, Nat

        # Compile `truediv` using float arithmetic
        [left, right] = args
        [left] = Nat.__float__.compile_call(
            self.builder, [left], [], self.globals, self.node
        )
        [right] = Nat.__float__.compile_call(
            self.builder, [right], [], self.globals, self.node
        )
        [out] = Float.__truediv__.compile_call(
            self.builder, [left, right], [], self.globals, self.node
        )
        return [out]


class IntTruedivCompiler(CustomCallCompiler):
    """Compiler for the `int.__truediv__` method."""

    def compile(self, args: list[Wire]) -> list[Wire]:
        from guppylang.prelude.builtins import Float, Int

        # Compile `truediv` using float arithmetic
        [left, right] = args
        [left] = Int.__float__.compile_call(
            self.builder, [left], [], self.globals, self.node
        )
        [right] = Int.__float__.compile_call(
            self.builder, [right], [], self.globals, self.node
        )
        [out] = Float.__truediv__.compile_call(
            self.builder, [left, right], [], self.globals, self.node
        )
        return [out]


class FloatBoolCompiler(CustomCallCompiler):
    """Compiler for the `float.__bool__` method."""

    def compile(self, args: list[Wire]) -> list[Wire]:
        from guppylang.prelude.builtins import Float

        # We have: bool(x) = (x != 0.0)
        zero = self.builder.load(hugr.std.float.FloatVal(0.0))
        [out] = Float.__ne__.compile_call(
            self.builder,
            [args[0], zero],
            [],
            self.globals,
            self.node,
        )
        return [out]


class FloatFloordivCompiler(CustomCallCompiler):
    """Compiler for the `float.__floordiv__` method."""

    def compile(self, args: list[Wire]) -> list[Wire]:
        from guppylang.prelude.builtins import Float

        # We have: floordiv(x, y) = floor(truediv(x, y))
        [div] = Float.__truediv__.compile_call(
            self.builder, args, [], self.globals, self.node
        )
        [floor] = Float.__floor__.compile_call(
            self.builder, [div], [], self.globals, self.node
        )
        return [floor]


class FloatModCompiler(CustomCallCompiler):
    """Compiler for the `float.__mod__` method."""

    def compile(self, args: list[Wire]) -> list[Wire]:
        from guppylang.prelude.builtins import Float

        # We have: mod(x, y) = x - (x // y) * y
        [div] = Float.__floordiv__.compile_call(
            self.builder, args, [], self.globals, self.node
        )
        [mul] = Float.__mul__.compile_call(
            self.builder, [div, args[1]], [], self.globals, self.node
        )
        [sub] = Float.__sub__.compile_call(
            self.builder, [args[0], mul], [], self.globals, self.node
        )
        return [sub]


class FloatDivmodCompiler(CustomCallCompiler):
    """Compiler for the `__divmod__` method."""

    def compile(self, args: list[Wire]) -> list[Wire]:
        from guppylang.prelude.builtins import Float

        # We have: divmod(x, y) = (div(x, y), mod(x, y))
        [div] = Float.__truediv__.compile_call(
            self.builder, args, [], self.globals, self.node
        )
        [mod] = Float.__mod__.compile_call(
            self.builder, args, [], self.globals, self.node
        )
        return self.builder.add(ops.MakeTuple()(div, mod))[:]


class MeasureCompiler(CustomCallCompiler):
    """Compiler for the `measure` function."""

    def compile(self, args: list[Wire]) -> list[Wire]:
        from guppylang.prelude.quantum import quantum_op

        [qubit] = args
        [qubit, bit] = self.builder.add_op(quantum_op("Measure"), qubit)
        self.builder.add_op(quantum_op("QFree"), qubit)
        return [bit]


class QAllocCompiler(CustomCallCompiler):
    """Compiler for the `qubit` function."""

    def compile(self, args: list[Wire]) -> list[Wire]:
        from guppylang.prelude.quantum import quantum_op

        assert not args, "qubit() does not take any arguments"
        qubit = self.builder.add_op(quantum_op("QAlloc"))
        qubit = self.builder.add_op(quantum_op("Reset"), qubit)
        return [qubit]
