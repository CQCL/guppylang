from guppy.decorator import guppy
from guppy.module import GuppyModule
from guppy.prelude.builtins import linst
from guppy.prelude.quantum import Qubit, h

import guppy.prelude.quantum as quantum


def test_types(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test(
        xs: linst[Qubit], ys: linst[tuple[int, Qubit]]
    ) -> tuple[linst[Qubit], linst[tuple[int, Qubit]]]:
        return xs, ys

    validate(module.compile())


def test_len(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test(xs: linst[Qubit]) -> tuple[int, linst[Qubit]]:
        return len(xs)

    validate(module.compile())


def test_literal(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test(q1: Qubit, q2: Qubit) -> linst[Qubit]:
        return [q1, h(q2)]

    validate(module.compile())


def test_arith(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test(xs: linst[Qubit], ys: linst[Qubit], q: Qubit) -> linst[Qubit]:
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
