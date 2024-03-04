from guppylang.decorator import guppy
from guppylang.hugr import tys
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import linst
from guppylang.prelude.quantum import Qubit

import guppylang.prelude.quantum as quantum
from guppylang.prelude.quantum import h, cx, measure_return, measure, t


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
        return measure_return(q)

    validate(module.compile())


def test_interleave(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy.declare(module)
    def f(q1: Qubit, q2: Qubit) -> tuple[Qubit, Qubit]: ...

    @guppy.declare(module)
    def g(q1: Qubit, q2: Qubit) -> tuple[Qubit, Qubit]: ...

    @guppy(module)
    def test(
        a: Qubit, b: Qubit, c: Qubit, d: Qubit
    ) -> tuple[Qubit, Qubit, Qubit, Qubit]:
        a, b = f(a, b)
        c, d = f(c, d)
        b, c = g(b, c)
        return a, b, c, d

    validate(module.compile())


def test_if(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test(b: bool) -> Qubit:
        if b:
            a = Qubit()
            q = h(a)
        else:
            q = Qubit()
        return q

    validate(module.compile())


def test_if_return(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test(b: bool) -> Qubit:
        if b:
            q = Qubit()
            return h(q)
        else:
            q = Qubit()
        return q

    validate(module.compile())


def test_measure(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test(q: Qubit, x: int) -> int:
        b = measure(q)
        return x

    validate(module.compile())


def test_return_call(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy.declare(module)
    def op(q: Qubit) -> Qubit: ...

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

    @guppy(module)
    def foo(i: bool) -> bool:
        b = False
        while True:
            q = Qubit()
            b ^= measure(q)
            if i == 0:
                break
            i -= 1
        return b


def test_for(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test(qs: linst[tuple[Qubit, Qubit]]) -> linst[Qubit]:
        rs: linst[Qubit] = []
        for q1, q2 in qs:
            q1, q2 = cx(q1, q2)
            rs += [q1, q2]
        return rs

    validate(module.compile())


def test_for_measure(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test(qs: linst[Qubit]) -> bool:
        parity = False
        for q in qs:
            parity |= measure(q)
        return parity

    validate(module.compile())


def test_for_continue(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test(qs: linst[Qubit]) -> int:
        x = 0
        for q in qs:
            if measure(q):
                continue
            x += 1
        return x

    validate(module.compile())


def test_for_nonlinear_break(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy.type(module, tys.TupleType(inner=[]))
    class MyIter:
        """An iterator that yields linear values but is not linear itself."""

        @guppy.declare(module)
        def __hasnext__(self: "MyIter") -> tuple[bool, "MyIter"]: ...

        @guppy.declare(module)
        def __next__(self: "MyIter") -> tuple[Qubit, "MyIter"]: ...

        @guppy.declare(module)
        def __end__(self: "MyIter") -> None: ...

    @guppy.type(module, tys.TupleType(inner=[]))
    class MyType:
        """Type that produces the iterator above."""

        @guppy.declare(module)
        def __iter__(self: "MyType") -> MyIter: ...

    @guppy.declare(module)
    def measure(q: Qubit) -> bool: ...

    @guppy(module)
    def test(mt: MyType, xs: list[int]) -> None:
        # We can break, since `mt` itself is not linear
        for q in mt:
            if measure(q):
                break

    validate(module.compile())


def test_rus(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def repeat_until_success(q: Qubit) -> Qubit:
        while True:
            aux, q = cx(t(h(Qubit())), q)
            aux, q = cx(h(aux), q)
            if measure(h(t(aux))):
                break
        return q
