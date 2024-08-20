import hugr
from hugr import Wire, ops
from hugr import tys as ht
from hugr.std.float import FLOAT_T
from hugr.std.int import INT_T

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
            [left],
            [],
            self.dfg,
            self.globals,
            self.node,
            ht.FunctionType([INT_T], [FLOAT_T]),
        )
        [right] = Nat.__float__.compile_call(
            [right],
            [],
            self.dfg,
            self.globals,
            self.node,
            ht.FunctionType([INT_T], [FLOAT_T]),
        )
        [out] = Float.__truediv__.compile_call(
            [left, right],
            [],
            self.dfg,
            self.globals,
            self.node,
            ht.FunctionType([FLOAT_T, FLOAT_T], [FLOAT_T]),
        )
        return [out]


class IntTruedivCompiler(CustomCallCompiler):
    """Compiler for the `int.__truediv__` method."""

    def compile(self, args: list[Wire]) -> list[Wire]:
        from guppylang.prelude.builtins import Float, Int

        # Compile `truediv` using float arithmetic
        [left, right] = args
        [left] = Int.__float__.compile_call(
            [left],
            [],
            self.dfg,
            self.globals,
            self.node,
            ht.FunctionType([INT_T], [FLOAT_T]),
        )
        [right] = Int.__float__.compile_call(
            [right],
            [],
            self.dfg,
            self.globals,
            self.node,
            ht.FunctionType([INT_T], [FLOAT_T]),
        )
        [out] = Float.__truediv__.compile_call(
            [left, right],
            [],
            self.dfg,
            self.globals,
            self.node,
            ht.FunctionType([FLOAT_T, FLOAT_T], [FLOAT_T]),
        )
        return [out]


class FloatBoolCompiler(CustomCallCompiler):
    """Compiler for the `float.__bool__` method."""

    def compile(self, args: list[Wire]) -> list[Wire]:
        from guppylang.prelude.builtins import Float

        # We have: bool(x) = (x != 0.0)
        zero = self.builder.load(hugr.std.float.FloatVal(0.0))
        [out] = Float.__ne__.compile_call(
            [args[0], zero],
            [],
            self.dfg,
            self.globals,
            self.node,
            ht.FunctionType([FLOAT_T, FLOAT_T], [ht.Bool]),
        )
        return [out]


class FloatFloordivCompiler(CustomCallCompiler):
    """Compiler for the `float.__floordiv__` method."""

    def compile(self, args: list[Wire]) -> list[Wire]:
        from guppylang.prelude.builtins import Float

        # We have: floordiv(x, y) = floor(truediv(x, y))
        [div] = Float.__truediv__.compile_call(
            args,
            [],
            self.dfg,
            self.globals,
            self.node,
            ht.FunctionType([FLOAT_T, FLOAT_T], [FLOAT_T]),
        )
        [floor] = Float.__floor__.compile_call(
            [div],
            [],
            self.dfg,
            self.globals,
            self.node,
            ht.FunctionType([FLOAT_T], [FLOAT_T]),
        )
        return [floor]


class FloatModCompiler(CustomCallCompiler):
    """Compiler for the `float.__mod__` method."""

    def compile(self, args: list[Wire]) -> list[Wire]:
        from guppylang.prelude.builtins import Float

        # We have: mod(x, y) = x - (x // y) * y
        [div] = Float.__floordiv__.compile_call(
            args,
            [],
            self.dfg,
            self.globals,
            self.node,
            ht.FunctionType([FLOAT_T] * len(args), [FLOAT_T]),
        )
        [mul] = Float.__mul__.compile_call(
            [div, args[1]],
            [],
            self.dfg,
            self.globals,
            self.node,
            ht.FunctionType([FLOAT_T, FLOAT_T], [FLOAT_T]),
        )
        [sub] = Float.__sub__.compile_call(
            [args[0], mul],
            [],
            self.dfg,
            self.globals,
            self.node,
            ht.FunctionType([FLOAT_T, FLOAT_T], [FLOAT_T]),
        )
        return [sub]


class FloatDivmodCompiler(CustomCallCompiler):
    """Compiler for the `__divmod__` method."""

    def compile(self, args: list[Wire]) -> list[Wire]:
        from guppylang.prelude.builtins import Float

        # We have: divmod(x, y) = (div(x, y), mod(x, y))
        [div] = Float.__truediv__.compile_call(
            args,
            [],
            self.dfg,
            self.globals,
            self.node,
            ht.FunctionType([FLOAT_T, FLOAT_T], [FLOAT_T]),
        )
        [mod] = Float.__mod__.compile_call(
            args,
            [],
            self.dfg,
            self.globals,
            self.node,
            ht.FunctionType([FLOAT_T] * len(args), [FLOAT_T]),
        )
        return list(self.builder.add(ops.MakeTuple()(div, mod)))


class MeasureCompiler(CustomCallCompiler):
    """Compiler for the `measure` function."""

    def compile(self, args: list[Wire]) -> list[Wire]:
        from guppylang.prelude.quantum import quantum_op

        [q] = args
        [q, bit] = self.builder.add_op(
            quantum_op("Measure")(ht.FunctionType([ht.Qubit], [ht.Qubit, ht.Bool]), []),
            q,
        )
        self.builder.add_op(quantum_op("QFree")(ht.FunctionType([ht.Qubit], []), []), q)
        return [bit]


class QAllocCompiler(CustomCallCompiler):
    """Compiler for the `qubit` function."""

    def compile(self, args: list[Wire]) -> list[Wire]:
        from guppylang.prelude.quantum import quantum_op

        assert not args, "qubit() does not take any arguments"
        q = self.builder.add_op(
            quantum_op("QAlloc")(ht.FunctionType([], [ht.Qubit]), [])
        )
        q = self.builder.add_op(
            quantum_op("Reset")(ht.FunctionType([ht.Qubit], [ht.Qubit]), []), q
        )
        return [q]
