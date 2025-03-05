from typing import no_type_check

from hugr import Wire
from hugr import tys as ht
from hugr.std.int import int_t

from guppylang.decorator import guppy
from guppylang.definition.custom import CustomInoutCallCompiler
from guppylang.definition.value import CallReturnWires
from guppylang.module import GuppyModule
from guppylang.std._internal.compiler.arithmetic import inarrow_s, iwiden_s
from guppylang.std._internal.compiler.prelude import build_unwrap_right
from guppylang.std._internal.compiler.quantum import (
    QSYSTEM_RANDOM_EXTENSION,
    RNGCONTEXT_T,
)
from guppylang.std._internal.util import external_op
from guppylang.std.builtins import nat, owned
from guppylang.std.option import Option

qsystem_random = GuppyModule("qsystem.random")


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


@guppy.hugr_op(
    external_op("NewRNGContext", [], ext=QSYSTEM_RANDOM_EXTENSION),
    module=qsystem_random,
)
@no_type_check
def _new_rng_context(seed: int) -> Option["RNG"]: ...


@guppy(qsystem_random)
def maybe_rng(seed: int) -> Option["RNG"]:  # type: ignore[type-arg] # "Option" expects no type arguments, but 1 given
    """Safely create a new random number generator using a seed.

    Returns `nothing` if RNG is already initialized."""
    return _new_rng_context(seed)  # type: ignore[no-any-return] # Returning Any from function declared to return "Option"


@guppy.type(RNGCONTEXT_T, copyable=False, droppable=False, module=qsystem_random)
class RNG:
    """Random number generator."""

    @guppy(qsystem_random)  # type: ignore[misc] # Unsupported decorated constructor type; Self argument missing for a non-static method (or an invalid type for self)
    def __new__(seed: int) -> "RNG":
        """Create a new random number generator using a seed."""
        return _new_rng_context(seed).unwrap()  # type: ignore[no-any-return] # Returning Any from function declared to return "RNGContext"

    @guppy.hugr_op(
        external_op("DeleteRNGContext", [], ext=QSYSTEM_RANDOM_EXTENSION),
        module=qsystem_random,
    )
    @no_type_check
    def discard(self: "RNG" @ owned) -> None: ...

    @guppy.custom(RandomIntCompiler(), module=qsystem_random)
    @no_type_check
    def random_int(self: "RNG") -> int: ...

    @guppy(qsystem_random)
    def random_nat(self: "RNG") -> nat:
        """Generate a random 32-bit natural number."""
        return nat(self.random_int())  # type: ignore[call-arg] # Too many arguments for "nat"

    @guppy.hugr_op(
        external_op("RandomFloat", [], ext=QSYSTEM_RANDOM_EXTENSION),
        module=qsystem_random,
    )
    @no_type_check
    def random_float(self: "RNG") -> float: ...

    @guppy.custom(RandomIntBoundedCompiler(), module=qsystem_random)
    @no_type_check
    def random_int_bounded(self: "RNG", bound: int) -> int: ...
