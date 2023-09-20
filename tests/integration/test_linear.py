from guppy.compiler import guppy, GuppyModule
from guppy.prelude.quantum import Qubit
from tests.integration.util import validate

import guppy.prelude.quantum as quantum
from guppy.prelude.quantum import h, cx


def test_id():
    module = GuppyModule("test")
    module.load(quantum)

    @module
    def test(q: Qubit) -> Qubit:
        return q

    validate(module.compile(True))


def test_assign():
    module = GuppyModule("test")
    module.load(quantum)

    @module
    def test(q: Qubit) -> Qubit:
        r = q
        s = r
        return s

    validate(module.compile(True))


def test_interleave():
    module = GuppyModule("test")
    module.load(quantum)

    @module.declare
    def f(q1: Qubit, q2: Qubit) -> tuple[Qubit, Qubit]:
        pass

    @module.declare
    def g(q1: Qubit, q2: Qubit) -> tuple[Qubit, Qubit]:
        pass

    @module
    def test(a: Qubit, b: Qubit, c: Qubit, d: Qubit) -> tuple[Qubit, Qubit, Qubit, Qubit]:
        a, b = f(a, b)
        c, d = f(c, d)
        b, c = g(b, c)
        return a, b, c, d

    validate(module.compile(True))


def test_if():
    module = GuppyModule("test")
    module.load(quantum)

    @module.declare
    def new() -> Qubit:
        pass

    @module
    def test(b: bool) -> Qubit:
        if b:
            a = new()
            q = h(a)
        else:
            q = new()
        return q

    validate(module.compile(True))


def test_if_return():
    module = GuppyModule("test")
    module.load(quantum)

    @module.declare
    def new() -> Qubit:
        pass

    @module
    def test(b: bool) -> Qubit:
        if b:
            q = new()
            return h(q)
        else:
            q = new()
        return q

    validate(module.compile(True))


def test_measure():
    module = GuppyModule("test")
    module.load(quantum)

    @module.declare
    def measure(q: Qubit) -> bool:
        pass

    @module
    def test(q: Qubit, x: int) -> int:
        b = measure(q)
        return x

    validate(module.compile(True))


def test_return_call():
    module = GuppyModule("test")
    module.load(quantum)

    @module.declare
    def op(q: Qubit) -> Qubit:
        pass

    @module
    def test(q: Qubit) -> Qubit:
        return op(q)

    validate(module.compile(True))


def test_while():
    module = GuppyModule("test")
    module.load(quantum)

    @module
    def test(q: Qubit, i: int) -> Qubit:
        while i > 0:
            i -= 1
            q = h(q)
        return q

    validate(module.compile(True))


def test_while_break():
    module = GuppyModule("test")
    module.load(quantum)

    @module
    def test(q: Qubit, i: int) -> Qubit:
        while i > 0:
            i -= 1
            q = h(q)
            if i < 5:
                break
        return q

    validate(module.compile(True))


def test_while_continue():
    module = GuppyModule("test")
    module.load(quantum)

    @module
    def test(q: Qubit, i: int) -> Qubit:
        while i > 0:
            i -= 1
            if i % 3 == 0:
                continue
            q = h(q)
        return q

    validate(module.compile(True))


def test_while_reset():
    module = GuppyModule("test")
    module.load(quantum)

    @module.declare
    def new_qubit() -> Qubit:
        pass

    @module.declare
    def measure() -> bool:
        pass

    @module
    def foo(i: bool) -> bool:
        b = False
        while True:
            q = new_qubit()
            b ^= measure(q)
            if i == 0:
                break
            i -= 1
        return b


def test_rus():
    module = GuppyModule("test")
    module.load(quantum)

    @module.declare
    def measure(q: Qubit) -> bool:
        pass

    @module.declare
    def qalloc() -> Qubit:
        pass

    @module.declare
    def t(q: Qubit) -> Qubit:
        pass

    @module
    def repeat_until_success(q: Qubit) -> Qubit:
        while True:
            aux, q = cx(t(h(qalloc())), q)
            aux, q = cx(h(aux), q)
            if measure(h(t(aux))):
                break
        return q
