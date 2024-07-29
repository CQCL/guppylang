from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import inout
from guppylang.prelude.quantum import qubit

import guppylang.prelude.quantum as quantum


def test_basic(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy.declare(module)
    def foo(q: qubit @inout) -> None: ...

    @guppy(module)
    def test(q: qubit) -> qubit:
        foo(q)
        return q

    validate(module.compile())


def test_mixed(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy.declare(module)
    def foo(q1: qubit @inout, q2: qubit) -> qubit: ...

    @guppy(module)
    def test(q1: qubit, q2: qubit) -> tuple[qubit, qubit]:
        q2 = foo(q1, q2)
        return q1, q2

    validate(module.compile())


def test_local(validate):
    module = GuppyModule("test")
    module.load(quantum)

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
    module.load(quantum)

    @guppy.declare(module)
    def foo(x: int, q: qubit @inout) -> int: ...

    @guppy(module)
    def test(q: qubit) -> tuple[int, qubit]:
        # This is legal since function arguments and tuples are evaluated left to right
        return foo(foo(foo(0, q), q), q), q

    validate(module.compile())


def test_struct(validate):
    module = GuppyModule("test")
    module.load(quantum)

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
        # bar(a)
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
    module.load(quantum)

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

