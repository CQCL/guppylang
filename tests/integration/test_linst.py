from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import linst
from guppylang.prelude.quantum import qubit, h

import guppylang.prelude.quantum as quantum


def test_types(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test(
        xs: linst[qubit], ys: linst[tuple[int, qubit]]
    ) -> tuple[linst[qubit], linst[tuple[int, qubit]]]:
        return xs, ys

    validate(module.compile())


def test_len(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test(xs: linst[qubit]) -> tuple[int, linst[qubit]]:
        return len(xs)

    validate(module.compile())


def test_literal(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test(q1: qubit, q2: qubit) -> linst[qubit]:
        return [q1, h(q2)]

    validate(module.compile())


def test_arith(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test(xs: linst[qubit], ys: linst[qubit], q: qubit) -> linst[qubit]:
        xs += [q]
        return xs + ys

    validate(module.compile())


def test_copyable(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test() -> linst[int]:
        xs: linst[int] = [1, 2, 3]
        ys: linst[int] = []
        return xs + xs

    validate(module.compile())
