"""Native arithmetic operations from the HUGR std, and compilers for non native ones."""

from collections.abc import Sequence

import hugr
from hugr import Wire, ops
from hugr import tys as ht
from hugr.std.float import FLOAT_T
from hugr.std.int import int_t

from guppylang.definition.custom import (
    CustomCallCompiler,
)
from guppylang.tys.ty import NumericType

INT_T = int_t(NumericType.INT_WIDTH)

# ------------------------------------------------------
# --------- std.arithmetic.int operations --------------
# ------------------------------------------------------


def _instantiate_int_op(
    name: str,
    int_width: int | Sequence[int],
    inp: list[ht.Type],
    out: list[ht.Type],
) -> ops.ExtOp:
    op_def = hugr.std.int.INT_OPS_EXTENSION.get_op(name)
    int_width = [int_width] if isinstance(int_width, int) else int_width
    return ops.ExtOp(
        op_def,
        ht.FunctionType(inp, out),
        [ht.BoundedNatArg(w) for w in int_width],
    )


def ieq(width: int) -> ops.ExtOp:
    """Returns a `std.arithmetic.int.ieq` operation."""
    return _instantiate_int_op("ieq", width, [int_t(width), int_t(width)], [ht.Bool])


def ine(width: int) -> ops.ExtOp:
    """Returns a `std.arithmetic.int.ine` operation."""
    return _instantiate_int_op("ine", width, [int_t(width), int_t(width)], [ht.Bool])


# ------------------------------------------------------
# --------- std.arithmetic.conversions ops -------------
# ------------------------------------------------------


def convert_ifromusize() -> ops.ExtOp:
    """Returns a `std.arithmetic.conversions.ifromusize` operation."""
    op_def = hugr.std.int.CONVERSIONS_EXTENSION.get_op("ifromusize")
    return ops.ExtOp(
        op_def,
        ht.FunctionType([ht.USize()], [int_t(6)]),
    )


def convert_itousize() -> ops.ExtOp:
    """Returns a `std.arithmetic.conversions.itousize` operation."""
    op_def = hugr.std.int.CONVERSIONS_EXTENSION.get_op("itousize")
    return ops.ExtOp(
        op_def,
        ht.FunctionType([int_t(6)], [ht.USize()]),
    )


def convert_ifrombool() -> ops.ExtOp:
    """Returns a `std.arithmetic.conversions.ifrombool` operation."""
    op_def = hugr.std.int.CONVERSIONS_EXTENSION.get_op("ifrombool")
    return ops.ExtOp(
        op_def,
        ht.FunctionType([ht.Bool], [int_t(1)]),
    )


def convert_itobool() -> ops.ExtOp:
    """Returns a `std.arithmetic.conversions.itobool` operation."""
    op_def = hugr.std.int.CONVERSIONS_EXTENSION.get_op("itobool")
    return ops.ExtOp(
        op_def,
        ht.FunctionType([int_t(1)], [ht.Bool]),
    )


# ------------------------------------------------------
# --------- Custom compilers for non-native ops --------
# ------------------------------------------------------


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
