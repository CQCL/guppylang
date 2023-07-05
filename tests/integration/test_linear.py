from guppy.compiler import guppy, GuppyModule
from tests.integration.util import validate, qubit


def test_id():
    @guppy
    def test(q: qubit) -> qubit:
        return q

    validate(test)


def test_assign():
    @guppy
    def test(q: qubit) -> qubit:
        r = q
        s = r
        return s

    validate(test)


def test_interleave():
    module = GuppyModule("test")

    @module.declare
    def f(q1: qubit, q2: qubit) -> tuple[qubit, qubit]:
        pass

    @module.declare
    def g(q1: qubit, q2: qubit) -> tuple[qubit, qubit]:
        pass

    @module
    def test(a: qubit, b: qubit, c: qubit, d: qubit) -> tuple[qubit, qubit, qubit, qubit]:
        a, b = f(a, b)
        c, d = f(c, d)
        b, c = g(b, c)
        return a, b, c, d

    validate(module.compile(True))


def test_if():
    module = GuppyModule("test")

    @module.declare
    def new() -> qubit:
        pass

    @module.declare
    def op(x: qubit) -> qubit:
        pass

    @module
    def test(b: bool) -> qubit:
        if b:
            a = new()
            q = op(a)
        else:
            q = new()
        return q

    validate(module.compile(True))


def test_if_return():
    module = GuppyModule("test")

    @module.declare
    def new() -> qubit:
        pass

    @module.declare
    def op(x: qubit) -> qubit:
        pass

    @module
    def test(b: bool) -> qubit:
        if b:
            q = new()
            return op(q)
        else:
            q = new()
        return q

    validate(module.compile(True))


def test_measure():
    module = GuppyModule("test")

    @module.declare
    def measure(q: qubit) -> bool:
        pass

    @module
    def test(q: qubit, x: int) -> int:
        b = measure(q)
        return x

    validate(module.compile(True))


def test_while():
    module = GuppyModule("test")

    @module.declare
    def op(q: qubit) -> qubit:
        pass

    @module
    def test(q: qubit, i: int) -> qubit:
        while i > 0:
            i -= 1
            q = op(q)
        return q

    validate(module.compile(True))


def test_while_break():
    module = GuppyModule("test")

    @module.declare
    def op(q: qubit) -> qubit:
        pass

    @module
    def test(q: qubit, i: int) -> qubit:
        while i > 0:
            i -= 1
            q = op(q)
            if i < 5:
                break
        return q

    validate(module.compile(True))


def test_while_continue():
    module = GuppyModule("test")

    @module.declare
    def op(q: qubit) -> qubit:
        pass

    @module
    def test(q: qubit, i: int) -> qubit:
        while i > 0:
            i -= 1
            if i % 3 == 0:
                continue
            q = op(q)
        return q

    validate(module.compile(True))


def test_while_reset():
    module = GuppyModule("test")

    @module.declare
    def new_qubit() -> qubit:
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
