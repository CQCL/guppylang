from typing import no_type_check

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std._internal.compiler.quantum import (
    QSYSTEM_RANDOM_EXTENSION,
    RNGCONTEXT_T,
)
from guppylang.std._internal.util import external_op
from guppylang.std.builtins import owned

qsystem_random = GuppyModule("qsystem.random")


@guppy.struct(qsystem_random)
class Random:
    ctx: "RNGContext"

    @guppy(qsystem_random)
    @no_type_check
    def random_int(self: "Random") -> int:
        self.ctx, rnd = self.ctx._random_int()
        return rnd

    @guppy(qsystem_random)
    @no_type_check
    def random_float(self: "Random") -> float:
        self.ctx, rnd = self.ctx._random_float()
        return rnd

    @guppy(qsystem_random)
    @no_type_check
    def random_int_bounded(self: "Random", bound: int) -> int:
        self.ctx, rnd = self.ctx._random_int_bounded(bound)
        return rnd


@guppy.type(RNGCONTEXT_T, copyable=False, module=qsystem_random)
class RNGContext:
    @guppy.hugr_op(
        external_op("NewRNGContext", [], ext=QSYSTEM_RANDOM_EXTENSION),
        module=qsystem_random,
    )
    @no_type_check
    # Initialize the random number generator.
    # Can only be initialised once per program. Second init fails at rutime.
    def __new__(seed: int) -> "RNGContext": ...

    # init safely, returning None if already acquired.
    # TODO: unsure if it's possible as a static method
    # def init_safe(seed: int) -> "RNGContext" | None:

    @guppy.hugr_op(
        external_op("DeleteRNGContext", [], ext=QSYSTEM_RANDOM_EXTENSION),
        module=qsystem_random,
    )
    @no_type_check
    # TODO: Should we be calling `__del__` somewhere?
    def discard(self: "RNGContext" @ owned) -> None: ...

    @guppy.hugr_op(
        external_op("RandomInt", [], ext=QSYSTEM_RANDOM_EXTENSION),
        module=qsystem_random,
    )
    @no_type_check
    def _random_int(self: "RNGContext") -> ("RNGContext", int): ...

    @guppy.hugr_op(
        external_op("RandomFloat", [], ext=QSYSTEM_RANDOM_EXTENSION),
        module=qsystem_random,
    )
    @no_type_check
    def _random_float(self: "RNGContext") -> ("RNGContext", float): ...

    @guppy.hugr_op(
        external_op(
            "RandomIntBounded", [], ext=QSYSTEM_RANDOM_EXTENSION
        ),
        module=qsystem_random,
    )
    @no_type_check
    def _random_int_bounded(self: "RNGContext", bound: int) -> ("RNGContext", int): ...
