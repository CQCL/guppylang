from guppylang import qubit
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.angles import angle
from guppylang.std.builtins import array
from guppylang.std.quantum import h, measure, cx, rz


def test_basics(validate):
    module = GuppyModule("module")
    module.load(qubit, h, cx, measure)

    @guppy.comptime(module)
    def foo() -> qubit:
        q = qubit()
        h(q)
        bar(q)
        return q

    @guppy.comptime(module)
    def bar(q1: qubit) -> None:
        q2 = qubit()
        cx(q1, q2)
        measure(q2)

    validate(module.compile())


def test_ladder(validate):
    module = GuppyModule("module")
    module.load(qubit, cx)

    @guppy.comptime(module)
    def test(qs: array[qubit, 10]) -> None:
        for q1, q2 in zip(qs[:-1], qs[1:]):
            cx(q1, q2)

    validate(module.compile())


def test_angles(validate):
    module = GuppyModule("module")
    module.load(qubit, rz, angle)

    @guppy.comptime(module)
    def test(qs: array[qubit, 10], theta: angle) -> None:
        for q in qs:
            rz(q, theta)
            theta /= 2

    validate(module.compile())
