from guppylang import qubit
from guppylang.decorator import guppy
from guppylang.std.angles import angle
from guppylang.std.builtins import array, barrier
from guppylang.std.quantum import h, measure, cx, rz, discard_array
import itertools


def test_basics(validate):
    @guppy.comptime
    def foo() -> qubit:
        q = qubit()
        h(q)
        bar(q)
        return q

    @guppy.comptime
    def bar(q1: qubit) -> None:
        q2 = qubit()
        cx(q1, q2)
        measure(q2)

    validate(foo.compile())


def test_ladder(validate):
    @guppy.comptime
    def test(qs: array[qubit, 10]) -> None:
        for q1, q2 in itertools.pairwise(qs):
            cx(q1, q2)

    validate(test.compile())


def test_angles(validate):
    @guppy.comptime
    def test(qs: array[qubit, 10], theta: angle) -> None:
        for q in qs:
            rz(q, theta)
            theta /= 2

    validate(test.compile())


def test_barrier_wrapper(validate):
    """Test workaround for https://github.com/CQCL/guppylang/issues/1189"""

    @guppy
    def barrier_wrapper(qs: array[qubit, 5]) -> None:
        barrier(qs)

    @guppy.comptime
    def main() -> None:
        qs = array(qubit() for _ in range(5))
        barrier_wrapper(qs)
        h(qs[0])
        discard_array(qs)

    validate(main.compile())
