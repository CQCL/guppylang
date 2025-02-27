from typing import no_type_check

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std._internal.compiler.quantum import (
    QSYSTEM_RANDOM_EXTENSION,
    RNGCONTEXT_T,
)
from guppylang.std._internal.util import external_op
from guppylang.std.builtins import owned
from guppylang.std.option import Option

qsystem_random = GuppyModule("qsystem.random")
qsystem_random.load(Option)  # type: ignore[arg-type] # Argument 1 to "load" of "GuppyModule" has incompatible type "type[Option]"; expected "Definition | GuppyModule | Module"


@guppy.hugr_op(
    external_op("NewRNGContext", [], ext=QSYSTEM_RANDOM_EXTENSION),
    module=qsystem_random,
)
@no_type_check
def _new_rng_context(seed: int) -> Option["RNG"]: ...


@guppy.type(RNGCONTEXT_T, copyable=False, droppable=False, module=qsystem_random)
class RNG:
    @guppy(qsystem_random)  # type: ignore[misc] # 27: Unsupported decorated constructor type # 28: Self argument missing for a non-static method (or an invalid type for self)
    def __new__(seed: int) -> "RNG":
        return _new_rng_context(seed).unwrap()  # type: ignore[no-any-return] # Returning Any from function declared to return "RNGContext"

    @guppy.hugr_op(
        external_op("DeleteRNGContext", [], ext=QSYSTEM_RANDOM_EXTENSION),
        module=qsystem_random,
    )
    @no_type_check
    # TODO: Should we be calling `__del__` somewhere?
    def discard(self: "RNG" @ owned) -> None: ...

    @guppy.hugr_op(
        external_op("RandomInt", [], ext=QSYSTEM_RANDOM_EXTENSION),
        module=qsystem_random,
    )
    @no_type_check
    def random_int(self: "RNG") -> int: ...

    @guppy.hugr_op(
        external_op("RandomFloat", [], ext=QSYSTEM_RANDOM_EXTENSION),
        module=qsystem_random,
    )
    @no_type_check
    def random_float(self: "RNG") -> float: ...

    @guppy.hugr_op(
        external_op("RandomIntBounded", [], ext=QSYSTEM_RANDOM_EXTENSION),
        module=qsystem_random,
    )
    @no_type_check
    def random_int_bounded(self: "RNG", bound: int) -> int: ...
