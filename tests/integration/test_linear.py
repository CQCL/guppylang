from guppy.decorator import guppy
from guppy.module import GuppyModule
from guppy.prelude.quantum import Qubit

import guppy.prelude.quantum as quantum
from guppy.prelude.quantum import h, cx, measure


def test_id(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test(q: Qubit) -> Qubit:
        return q

    validate(module.compile())


def test_assign(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test(q: Qubit) -> Qubit:
        r = q
        s = r
        return s

    validate(module.compile())


def test_linear_return_order(validate):
    # See https://github.com/CQCL-DEV/guppy/issues/35
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test(q: Qubit) -> tuple[Qubit, bool]:
        return measure(q)

    validate(module.compile())


def test_interleave(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy.declare(module)
    def f(q1: Qubit, q2: Qubit) -> tuple[Qubit, Qubit]:
        ...

    @guppy.declare(module)
    def g(q1: Qubit, q2: Qubit) -> tuple[Qubit, Qubit]:
        ...

    @guppy(module)
    def test(a: Qubit, b: Qubit, c: Qubit, d: Qubit) -> tuple[Qubit, Qubit, Qubit, Qubit]:
        a, b = f(a, b)
        c, d = f(c, d)
        b, c = g(b, c)
        return a, b, c, d

    validate(module.compile())


def test_if(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy.declare(module)
    def new() -> Qubit:
        ...

    @guppy(module)
    def test(b: bool) -> Qubit:
        if b:
            a = new()
            q = h(a)
        else:
            q = new()
        return q

    validate(module.compile())


def test_if_return(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy.declare(module)
    def new() -> Qubit:
        ...

    @guppy(module)
    def test(b: bool) -> Qubit:
        if b:
            q = new()
            return h(q)
        else:
            q = new()
        return q

    validate(module.compile())


def test_measure(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy.declare(module)
    def measure(q: Qubit) -> bool:
        ...

    @guppy(module)
    def test(q: Qubit, x: int) -> int:
        b = measure(q)
        return x

    validate(module.compile())


def test_return_call(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy.declare(module)
    def op(q: Qubit) -> Qubit:
        ...

    @guppy(module)
    def test(q: Qubit) -> Qubit:
        return op(q)

    validate(module.compile())


def test_while(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test(q: Qubit, i: int) -> Qubit:
        while i > 0:
            i -= 1
            q = h(q)
        return q

    validate(module.compile())


def test_while_break(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test(q: Qubit, i: int) -> Qubit:
        while i > 0:
            i -= 1
            q = h(q)
            if i < 5:
                break
        return q

    validate(module.compile())


def test_while_continue(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test(q: Qubit, i: int) -> Qubit:
        while i > 0:
            i -= 1
            if i % 3 == 0:
                continue
            q = h(q)
        return q

    validate(module.compile())


def test_while_reset(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy.declare(module)
    def new_qubit() -> Qubit:
        ...

    @guppy.declare(module)
    def measure() -> bool:
        ...

    @guppy(module)
    def foo(i: bool) -> bool:
        b = False
        while True:
            q = new_qubit()
            b ^= measure(q)
            if i == 0:
                break
            i -= 1
        return b


def test_rus(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy.declare(module)
    def measure(q: Qubit) -> bool:
        ...

    @guppy.declare(module)
    def qalloc() -> Qubit:
        ...

    @guppy.declare(module)
    def t(q: Qubit) -> Qubit:
        ...

    @guppy(module)
    def repeat_until_success(q: Qubit) -> Qubit:
        while True:
            aux, q = cx(t(h(qalloc())), q)
            aux, q = cx(h(aux), q)
            if measure(h(t(aux))):
                break
        return q
