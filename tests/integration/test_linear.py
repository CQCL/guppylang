from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import linst
from guppylang.prelude.quantum import qubit

import guppylang.prelude.quantum as quantum
from guppylang.prelude.quantum import h, cx, measure_return, measure, t
from guppylang.tys.ty import NoneType


def test_id(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test(q: qubit) -> qubit:
        return q

    validate(module.compile())


def test_assign(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test(q: qubit) -> qubit:
        r = q
        s = r
        return s

    validate(module.compile())


def test_linear_return_order(validate):
    # See https://github.com/CQCL-DEV/guppy/issues/35
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test(q: qubit) -> tuple[qubit, bool]:
        return measure_return(q)

    validate(module.compile())


def test_interleave(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy.declare(module)
    def f(q1: qubit, q2: qubit) -> tuple[qubit, qubit]: ...

    @guppy.declare(module)
    def g(q1: qubit, q2: qubit) -> tuple[qubit, qubit]: ...

    @guppy(module)
    def test(
        a: qubit, b: qubit, c: qubit, d: qubit
    ) -> tuple[qubit, qubit, qubit, qubit]:
        a, b = f(a, b)
        c, d = f(c, d)
        b, c = g(b, c)
        return a, b, c, d

    validate(module.compile())


def test_linear_struct(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy.struct(module)
    class MyStruct:
        q1: qubit
        q2: qubit

    @guppy.declare(module)
    def f(q1: qubit, q2: qubit) -> tuple[qubit, qubit]: ...

    @guppy.declare(module)
    def g(q1: qubit, q2: qubit) -> tuple[qubit, qubit]: ...

    @guppy(module)
    def test(s: MyStruct, t: MyStruct) -> tuple[qubit, qubit, qubit, qubit]:
        s.q1, s.q2 = f(s.q2, s.q1)
        t.q1, t.q2 = f(t.q1, t.q2)
        s.q2, t.q1 = g(t.q1, s.q2)
        return s.q1, s.q2, t.q1, t.q2

    validate(module.compile())


def test_mixed_classical_linear_struct(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy.struct(module)
    class MyStruct:
        q: qubit
        x: int
        y: float

    @guppy.declare(module)
    def f(q: qubit) -> qubit: ...

    @guppy(module)
    def test1(s: MyStruct) -> tuple[MyStruct, float]:
        a = s.x + s.y
        s.q = f(s.q)
        return s, a * s.x

    @guppy(module)
    def test2(s: MyStruct) -> tuple[MyStruct, int, int, int]:
        t = s
        u = t
        u.q = f(u.q)
        return u, s.x, t.x, u.x

    validate(module.compile())


def test_drop_classical_field(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy.struct(module)
    class MyStruct:
        q: qubit
        x: int

    @guppy.declare(module)
    def f() -> MyStruct: ...

    @guppy(module)
    def test() -> qubit:
        return f().q


def test_if(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test(b: bool) -> qubit:
        if b:
            a = qubit()
            q = h(a)
        else:
            q = qubit()
        return q

    validate(module.compile())


def test_if_return(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test(b: bool) -> qubit:
        if b:
            q = qubit()
            return h(q)
        else:
            q = qubit()
        return q

    validate(module.compile())


def test_if_struct_rebuild(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy.struct(module)
    class MyStruct:
        q: qubit

    @guppy(module)
    def test1(s: MyStruct, b: bool) -> MyStruct:
        if b:
            s = MyStruct(s.q)
        return s

    @guppy(module)
    def test2(s: MyStruct, b: bool) -> MyStruct:
        if b:
            s.q = s.q
        return s

    validate(module.compile())


def test_struct_reassign(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy.struct(module)
    class MyStruct1:
        x: "MyStruct2"

    @guppy.struct(module)
    class MyStruct2:
        q: qubit

    @guppy.declare(module)
    def consume(s: MyStruct2) -> None: ...

    @guppy(module)
    def test(s: MyStruct2, b: bool) -> MyStruct2:
        consume(s)
        if b:
            s = MyStruct2(qubit())
            return s
        else:
            s = MyStruct1(MyStruct2(qubit()))
        return s.x


def test_measure(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test(q: qubit, x: int) -> int:
        b = measure(q)
        return x

    validate(module.compile())


def test_return_call(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy.declare(module)
    def op(q: qubit) -> qubit: ...

    @guppy(module)
    def test(q: qubit) -> qubit:
        return op(q)

    validate(module.compile())


def test_while(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test(q: qubit, i: int) -> qubit:
        while i > 0:
            i -= 1
            q = h(q)
        return q

    validate(module.compile())


def test_while_break(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test(q: qubit, i: int) -> qubit:
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
    def test(q: qubit, i: int) -> qubit:
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
            q = qubit()
            b ^= measure(q)
            if i == 0:
                break
            i -= 1
        return b


def test_for(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test(qs: linst[tuple[qubit, qubit]]) -> linst[qubit]:
        rs: linst[qubit] = []
        for q1, q2 in qs:
            q1, q2 = cx(q1, q2)
            rs += [q1, q2]
        return rs

    validate(module.compile())


def test_for_measure(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test(qs: linst[qubit]) -> bool:
        parity = False
        for q in qs:
            parity |= measure(q)
        return parity

    validate(module.compile())


def test_for_continue(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test(qs: linst[qubit]) -> int:
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

    @guppy.type(module, NoneType().to_hugr())
    class MyIter:
        """An iterator that yields linear values but is not linear itself."""

        @guppy.declare(module)
        def __hasnext__(self: "MyIter") -> tuple[bool, "MyIter"]: ...

        @guppy.declare(module)
        def __next__(self: "MyIter") -> tuple[qubit, "MyIter"]: ...

        @guppy.declare(module)
        def __end__(self: "MyIter") -> None: ...

    @guppy.type(module, NoneType().to_hugr())
    class MyType:
        """Type that produces the iterator above."""

        @guppy.declare(module)
        def __iter__(self: "MyType") -> MyIter: ...

    @guppy.declare(module)
    def measure(q: qubit) -> bool: ...

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
    def repeat_until_success(q: qubit) -> qubit:
        while True:
            aux, q = cx(t(h(qubit())), q)
            aux, q = cx(h(aux), q)
            if measure(h(t(aux))):
                break
        return q
