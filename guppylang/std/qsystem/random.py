# mypy: disable-error-code="no-any-return"
from typing import Generic, no_type_check

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std._internal.compiler.qsystem import (
    RandomIntBoundedCompiler,
    RandomIntCompiler,
)
from guppylang.std._internal.compiler.quantum import (
    RNGCONTEXT_T,
)
from guppylang.std._internal.compiler.tket2_exts import QSYSTEM_RANDOM_EXTENSION
from guppylang.std._internal.util import external_op
from guppylang.std.angles import angle, pi
from guppylang.std.builtins import array, mem_swap, owned, panic
from guppylang.std.option import Option

qsystem_random = GuppyModule("qsystem.random")

qsystem_random.load(angle, pi)  # type: ignore[arg-type]

SHUFFLE_N = guppy.nat_var("SHUFFLE_N", module=qsystem_random)
SHUFFLE_T = guppy.type_var(
    "SHUFFLE_T", copyable=False, droppable=False, module=qsystem_random
)

DISCRETE_N = guppy.nat_var("DISCRETE_N", module=qsystem_random)


@guppy.hugr_op(
    external_op("NewRNGContext", [], ext=QSYSTEM_RANDOM_EXTENSION),
    module=qsystem_random,
)
@no_type_check
def _new_rng_context(seed: int) -> Option["RNG"]: ...


@guppy.type(RNGCONTEXT_T, copyable=False, droppable=False, module=qsystem_random)
class RNG:
    """Random number generator."""

    @guppy(qsystem_random)  # type: ignore[misc] # Unsupported decorated constructor type; Self argument missing for a non-static method (or an invalid type for self)
    def __new__(seed: int) -> "RNG":
        """Create a new random number generator using a seed."""
        return _new_rng_context(seed).unwrap()

    @guppy(qsystem_random)
    def discard(self: "RNG" @ owned) -> None:  # type: ignore[valid-type] # Invalid type comment or annotation
        """Discard the random number generator."""
        self._discard()

    @guppy(qsystem_random)
    def random_int(self: "RNG") -> int:
        """Generate a random 32-bit signed integer."""
        return self._random_int()

    @guppy(qsystem_random)
    def random_float(self: "RNG") -> float:
        """Generate a random floating point value in the range [0,1)."""
        return self._random_float()

    @guppy(qsystem_random)
    def random_int_bounded(self: "RNG", bound: int) -> int:
        """Generate a random 32-bit integer in the range [0, bound).

        Args:
            bound: The upper bound of the range, needs to less than 2^31.
        """
        return self._random_int_bounded(bound)

    @guppy(qsystem_random)
    def random_angle(self: "RNG") -> angle:
        """Generate a random angle in the range [-pi, pi)."""
        return (2.0 * self._random_float() - 1.0) * pi

    @guppy.hugr_op(
        external_op("DeleteRNGContext", [], ext=QSYSTEM_RANDOM_EXTENSION),
        module=qsystem_random,
    )
    @no_type_check
    def _discard(self: "RNG" @ owned) -> None: ...

    @guppy.custom(RandomIntCompiler(), module=qsystem_random)
    @no_type_check
    def _random_int(self: "RNG") -> int: ...

    @guppy.hugr_op(
        external_op("RandomFloat", [], ext=QSYSTEM_RANDOM_EXTENSION),
        module=qsystem_random,
    )
    @no_type_check
    def _random_float(self: "RNG") -> float: ...

    @guppy.custom(RandomIntBoundedCompiler(), module=qsystem_random)
    @no_type_check
    def _random_int_bounded(self: "RNG", bound: int) -> int: ...

    @guppy(qsystem_random)
    @no_type_check
    def shuffle(self: "RNG", array: array[SHUFFLE_T, SHUFFLE_N]) -> None:
        """Randomly shuffle the elements of a possibly linear array in place.
        Uses the Fisher-Yates algorithm."""
        for k in range(SHUFFLE_N):
            i = SHUFFLE_N - 1 - k
            j = self.random_int_bounded(i + 1)
            # TODO use array swap once lowering implemented
            # https://github.com/CQCL/guppylang/issues/924
            if i != j:
                mem_swap(array[i], array[j])


@guppy.struct(qsystem_random)
class DiscreteDistribution(Generic[DISCRETE_N]):  # type: ignore[misc]
    """A generic probability distribution over the set {0, 1, 2, ... DISCRETE_N - 1}.

    The `sums` array represents the cumulative probability distribution. That is,
    sums[i] is the probability of drawing a value <= i from the distribution.
    """

    sums: array[float, DISCRETE_N]  # type: ignore[valid-type]

    @guppy(qsystem_random)
    @no_type_check
    def sample(self: "DiscreteDistribution[DISCRETE_N]", rng: RNG) -> int:
        """Return a sample value from the distribution."""
        x = rng.random_float()
        # Use binary search to find the least i s.t. sums[i] >= x.
        i_min = 0
        i_max = DISCRETE_N - 1
        while i_min < i_max:
            i = (i_min + i_max) // 2
            if self.sums[i] >= x:
                i_max = i
            else:
                i_min = i + 1
        return i_min


@guppy(qsystem_random)
@no_type_check
def make_discrete_distribution(
    weights: array[float, DISCRETE_N],
) -> DiscreteDistribution[DISCRETE_N]:
    """Construct a discrete probability distribution over the set
    {0, 1, 2, ... DISCRETE_N - 1}, given as an array of weights which represent
    probabilities. The weights need not be normalized, but must be non-negative and not
    all zero."""
    W = 0.0
    for w in weights.copy():
        if w < 0.0:
            panic("Negative weight included in discrete distribution.")
        W += w
    if W == 0.0:
        panic("No positive weights included in discrete distribution.")
    sums = array(0.0 for _ in range(DISCRETE_N))
    s = 0.0
    for i in range(DISCRETE_N - 1):
        s += weights[i]
        sums[i] = s / W
    sums[DISCRETE_N - 1] = 1.0
    return DiscreteDistribution(sums)
