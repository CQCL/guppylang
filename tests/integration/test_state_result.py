from typing import no_type_check

from guppylang import decorator
from guppylang.module import GuppyModule
from guppylang.std.builtins import state_result, array, owned
from guppylang.std.quantum import qubit, discard, x, h
from guppylang.std import quantum

from tests.integration.test_quantum import compile_quantum_guppy


def test_basic(validate):
    @compile_quantum_guppy
    def main() -> None:
        q1 = qubit()
        q2 = qubit()
        state_result("tag", q1, q2)
        discard(q1)
        discard(q2)

    validate(main)


def test_empty(validate):
    @compile_quantum_guppy
    def main() -> None:
        state_result("tag")

    validate(main)


def test_multi(validate):
    @compile_quantum_guppy
    @no_type_check
    def main() -> None:
        q1 = qubit()
        q2 = qubit()
        state_result("tag1", q1, q2)
        q.x(q1)
        state_result("tag2", q1)
        discard(q1)
        discard(q2)

    validate(main)


def test_array(validate):
    @compile_quantum_guppy
    @no_type_check
    def main() -> None:
        qs = array(qubit() for _ in range(4))
        q.h(qs[1])
        q.h(qs[2])
        state_result("a", qs[1], qs[2], qs[3])
        state_result("b", qs[1])
        q.h(qs[3])

        q.cx(qs[1], qs[2])
        state_result("c", qs[2], qs[3])
        q.cx(qs[3], qs[4])
        discard_array(qs)

    validate(main)


def test_struct(validate):
    """Barrier on array/struct access."""

    module = GuppyModule("module")
    module.load(qubit, discard)
    module.load(q=quantum)

    @decorator.guppy.struct(module)
    class S:
        q1: qubit
        q2: qubit
        q3: qubit
        q4: qubit

    @decorator.guppy(module)
    @no_type_check
    def test(qs: S @ owned) -> None:
        q.h(qs.q1)
        q.h(qs.q2)
        state_result("1", qs.q1, qs.q2, qs.q3)
        state_result("2", qs.q1)
        q.h(qs.q3)

        q.cx(qs.q1, qs.q2)
        state_result("3", qs.q2, qs.q3)
        q.cx(qs.q3, qs.q4)

        discard(qs.q1)
        discard(qs.q2)
        discard(qs.q3)
        discard(qs.q4)

    validate(module.compile())
