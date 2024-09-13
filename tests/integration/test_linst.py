from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import linst, owned
from guppylang.prelude.quantum import qubit
from guppylang.prelude.quantum_functional import h

import guppylang.prelude.quantum_functional as quantum_functional


def test_types(validate):
    module = GuppyModule("test")
    module.load_all(quantum_functional)
    module.load(qubit)

    @guppy(module)
    def test(
        xs: linst[qubit] @owned, ys: linst[tuple[int, qubit]] @owned
    ) -> tuple[linst[qubit], linst[tuple[int, qubit]]]:
        return xs, ys

    validate(module.compile())


def test_len(validate):
    module = GuppyModule("test")
    module.load_all(quantum_functional)
    module.load(qubit)

    @guppy(module)
    def test(xs: linst[qubit] @owned) -> tuple[int, linst[qubit]]:
        return len(xs)

    validate(module.compile())


def test_literal(validate):
    module = GuppyModule("test")
    module.load_all(quantum_functional)
    module.load(qubit)

    @guppy(module)
    def test(q1: qubit @owned, q2: qubit @owned) -> linst[qubit]:
        return [q1, h(q2)]

    validate(module.compile())


def test_arith(validate):
    module = GuppyModule("test")
    module.load_all(quantum_functional)
    module.load(qubit)

    @guppy(module)
    def test(xs: linst[qubit] @owned, ys: linst[qubit] @owned, q: qubit @owned) -> linst[qubit]:
        xs += [q]
        return xs + ys

    validate(module.compile())


def test_copyable(validate):
    module = GuppyModule("test")

    @guppy(module)
    def test() -> linst[int]:
        xs: linst[int] = [1, 2, 3]
        ys: linst[int] = []
        return xs + xs

    validate(module.compile())
