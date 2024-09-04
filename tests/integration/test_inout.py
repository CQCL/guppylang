import pytest

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import inout
from guppylang.prelude.quantum import qubit

import guppylang.prelude.quantum as quantum


def test_basic(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.declare(module)
    def foo(q: qubit @inout) -> None: ...

    @guppy(module)
    def test(q: qubit) -> qubit:
        foo(q)
        return q

    validate(module.compile())


def test_mixed(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.declare(module)
    def foo(q1: qubit @inout, q2: qubit) -> qubit: ...

    @guppy(module)
    def test(q1: qubit, q2: qubit) -> tuple[qubit, qubit]:
        q2 = foo(q1, q2)
        return q1, q2

    validate(module.compile())


def test_local(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.declare(module)
    def foo(q: qubit @inout) -> None: ...

    @guppy(module)
    def test(q: qubit) -> qubit:
        f = foo
        f(q)
        return q

    validate(module.compile())


def test_nested_calls(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.declare(module)
    def foo(x: int, q: qubit @inout) -> int: ...

    @guppy(module)
    def test(q: qubit) -> tuple[int, qubit]:
        # This is legal since function arguments and tuples are evaluated left to right
        return foo(foo(foo(0, q), q), q), q

    validate(module.compile())


def test_struct(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.struct(module)
    class MyStruct:
        q1: qubit
        q2: qubit

    @guppy.declare(module)
    def foo(q1: qubit @inout, q2: qubit @inout) -> None: ...

    @guppy.declare(module)
    def bar(a: MyStruct @inout) -> None: ...

    @guppy(module)
    def test1(a: MyStruct) -> MyStruct:
        foo(a.q1, a.q2)
        bar(a)
        return a

    @guppy(module)
    def test2(a: MyStruct) -> MyStruct:
        bar(a)
        foo(a.q1, a.q2)
        bar(a)
        return a

    validate(module.compile())


def test_control_flow(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.declare(module)
    def foo(q: qubit @inout) -> None: ...

    @guppy.declare(module)
    def bar(q: qubit @inout) -> bool: ...

    @guppy(module)
    def test(q1: qubit, q2: qubit, n: int) -> tuple[qubit, qubit]:
        i = 0
        while i < n:
            foo(q1)
            if bar(q1) or bar(q2):
                foo(q2)
                continue
            elif not bar(q2):
                return q1, q2
            foo(q1)
            if bar(q2):
                foo(q1)
                break
            else:
                foo(q2)
            foo(q2)
            foo(q1)
            if bar(q2) and bar(q1):
                if i > 5:
                    foo(q2)
                return q1, q2
            foo(q1)
            i += 1
        return q1, q2

    validate(module.compile())


def test_tensor(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.struct(module)
    class A:
        q: qubit

    @guppy.struct(module)
    class B:
        q: qubit
        x: int

    @guppy.struct(module)
    class C:
        q: qubit
        x: float

    @guppy.declare(module)
    def foo(a: A @ inout, x: int) -> None: ...

    @guppy.declare(module)
    def bar(y: float, b: B @ inout, c: C) -> C: ...

    @guppy.declare(module)
    def baz(c: C @ inout) -> None: ...

    @guppy(module)
    def test(a: A, b: B, c1: C, c2: C, x: bool) -> tuple[A, B, C, C]:
        c1 = (foo, bar, baz)(a, b.x, c1.x, b, c1, c2)
        if x:
            c1 = ((foo, bar), baz)(a, b.x, c1.x, b, c1, c2)
        c1 = (foo, (bar, baz))(a, b.x, c1.x, b, c1, c2)
        return a, b, c1, c2

    validate(module.compile())


def test_basic_def(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.declare(module)
    def h(q: qubit @inout) -> None: ...

    @guppy(module)
    def foo(q: qubit @inout) -> None:
        h(q)
        h(q)

    @guppy(module)
    def test(q: qubit) -> qubit:
        foo(q)
        foo(q)
        return q

    validate(module.compile())


def test_empty_def(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy(module)
    def test(q: qubit @inout) -> None:
        pass

    @guppy(module)
    def main(q: qubit) -> qubit:
        test(q)
        return q

    validate(module.compile())


def test_mixed_def(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.declare(module)
    def foo(q: qubit @ inout) -> None: ...

    @guppy(module)
    def test(
        b: int, c: qubit @inout, d: float, a: tuple[qubit, qubit] @inout, e: qubit
    ) -> tuple[qubit, float]:
        foo(c)
        return e, b + d

    validate(module.compile())


def test_move_back(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.struct(module)
    class MyStruct:
        q: qubit

    @guppy.declare(module)
    def use(q: qubit) -> None: ...

    @guppy(module)
    def foo(s: MyStruct @inout) -> None:
        use(s.q)
        s.q = qubit()

    @guppy(module)
    def bar(s: MyStruct @inout) -> None:
        s.q = s.q

    @guppy(module)
    def swap(s: MyStruct @inout, t: MyStruct @inout) -> None:
        s.q, t.q = t.q, s.q

    @guppy(module)
    def main(s: MyStruct, t: MyStruct) -> MyStruct:
        foo(s)
        swap(s, t)
        bar(t)
        use(t.q)
        return s

    validate(module.compile())


def test_move_back_branch(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.struct(module)
    class MyStruct:
        q: qubit

    @guppy.declare(module)
    def use(q: qubit) -> None: ...

    @guppy(module)
    def test(s: MyStruct @inout, b: bool, n: int, q1: qubit, q2: qubit) -> None:
        use(s.q)
        if b:
            s.q = q1
            use(q2)
        else:
            s.q = q2
            use(q1)
        use(s.q)
        i = 0
        while True:
            if i == n:
                s.q = qubit()
                return
            i += 1
        # Guppy is not yet smart enough to detect that this code is unreachable
        s.q = qubit()
        return

    @guppy(module)
    def main(s: MyStruct) -> MyStruct:
        test(s, False, 5, qubit(), qubit())
        return s

    validate(module.compile())


def test_self(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.declare(module)
    def foo(q: qubit @inout) -> None: ...

    @guppy.struct(module)
    class MyStruct:
        q: qubit

        @guppy(module)
        def bar(self: "MyStruct" @inout, b: bool) -> None:
            foo(self.q)
            if b:
                foo(self.q)

    validate(module.compile())
