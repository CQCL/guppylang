from hugr import Wire
from hugr import tys as ht
from hugr.std.int import int_t

from guppylang.definition.custom import CustomInoutCallCompiler
from guppylang.definition.value import CallReturnWires
from guppylang.std._internal.compiler.arithmetic import inarrow_s, iwiden_s
from guppylang.std._internal.compiler.prelude import build_unwrap_right
from guppylang.std._internal.compiler.quantum import (
    QSYSTEM_RANDOM_EXTENSION,
    RNGCONTEXT_T,
)
from guppylang.std._internal.util import external_op


class RandomIntCompiler(CustomInoutCallCompiler):
    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        [ctx] = args
        [rnd, ctx] = self.builder.add_op(
            external_op("RandomInt", [], ext=QSYSTEM_RANDOM_EXTENSION)(
                ht.FunctionType([RNGCONTEXT_T], [int_t(5), RNGCONTEXT_T]), []
            ),
            ctx,
        )
        [rnd] = self.builder.add_op(iwiden_s(5, 6), rnd)
        return CallReturnWires(regular_returns=[rnd], inout_returns=[ctx])


class RandomIntBoundedCompiler(CustomInoutCallCompiler):
    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        [ctx, bound] = args
        bound_sum = self.builder.add_op(inarrow_s(6, 5), bound)
        bound = build_unwrap_right(
            self.builder, bound_sum, "bound must be a 32-bit integer"
        )
        [rnd, ctx] = self.builder.add_op(
            external_op("RandomIntBounded", [], ext=QSYSTEM_RANDOM_EXTENSION)(
                ht.FunctionType([RNGCONTEXT_T, int_t(5)], [int_t(5), RNGCONTEXT_T]), []
            ),
            ctx,
            bound,
        )
        [rnd] = self.builder.add_op(iwiden_s(5, 6), rnd)
        return CallReturnWires(regular_returns=[rnd], inout_returns=[ctx])
