import pytest
from guppylang import qubit, guppy, GuppyModule
from guppylang.std import quantum
from guppylang.std.angles import angle
from guppylang.std.builtins import owned
from guppylang.std.quantum import cx, rz
from guppylang.std.quantum_functional import quantum_functional, h

from tests.util import compile_guppy


def test_types(validate):
    @compile_guppy
    def test(
        xs: list[int], ys: list[tuple[int, float]]
    ) -> tuple[list[int], list[tuple[int, float]]]:
        return xs, ys

    validate(test)


def test_len(validate):
    @compile_guppy
    def test(xs: list[int]) -> int:
        return len(xs)

    validate(test)


def test_literal(validate):
    @compile_guppy
    def test(x: float) -> list[float]:
        return [1.0, 2.0, 3.0, 4.0 + x]

    validate(test)


def test_literal_linear(validate):
    module = GuppyModule("test")
    module.load_all(quantum_functional)
    module.load(qubit)

    @guppy(module)
    def test(q1: qubit @owned, q2: qubit @owned) -> list[qubit]:
        return [q1, h(q2)]

    validate(module.compile())


def test_push_pop(validate):
    @compile_guppy
    def test(xs: list[int]) -> bool:
        xs.append(3)
        x = xs.pop()
        return x == 3

    validate(test)


@pytest.mark.skip("See https://github.com/CQCL/guppylang/issues/528")
def test_arith(validate):
    @compile_guppy
    def test(xs: list[int]) -> list[int]:
        xs += xs + [42]
        xs = 3 * xs
        return xs * 4

    validate(test)


@pytest.mark.skip("See https://github.com/CQCL/guppylang/issues/528")
def test_arith_linear(validate):
    module = GuppyModule("test")
    module.load_all(quantum_functional)
    module.load(qubit)

    @guppy(module)
    def test(xs: list[qubit] @owned, ys: list[qubit] @owned, q: qubit @owned) -> list[qubit]:
        xs += [q]
        return xs + ys

    validate(module.compile())


def test_subscript(validate):
    @compile_guppy
    def test(xs: list[float], i: int) -> float:
        return xs[2 * i]

    validate(test)


def test_linear(validate):
    module = GuppyModule("test")
    module.load(qubit)

    @guppy(module)
    def test(xs: list[qubit], q: qubit @owned) -> int:
        xs.append(q)
        return len(xs)

    validate(module.compile())


def test_subscript_drop_rest(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.declare(module)
    def foo() -> list[int]: ...

    @guppy(module)
    def main() -> int:
        return foo()[0]

    validate(module.compile())


def test_linear_subscript(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.declare(module)
    def foo(q: qubit) -> None: ...

    @guppy(module)
    def main(qs: list[qubit] @owned, i: int) -> list[qubit]:
        foo(qs[i])
        return qs

    validate(module.compile())


def test_inout_subscript(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.declare(module)
    def foo(q: qubit) -> None: ...

    @guppy(module)
    def main(qs: list[qubit], i: int) -> None:
        foo(qs[i])

    validate(module.compile())


def test_multi_subscripts(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.declare(module)
    def foo(q1: qubit, q2: qubit) -> None: ...

    @guppy(module)
    def main(qs: list[qubit] @owned) -> list[qubit]:
        foo(qs[0], qs[1])
        foo(qs[0], qs[0])  # Will panic at runtime
        return qs

    validate(module.compile())


def test_struct_list(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.struct(module)
    class S:
        q1: qubit
        q2: qubit

    @guppy.declare(module)
    def foo(q1: qubit, q2: qubit) -> None: ...

    @guppy(module)
    def main(ss: list[S] @owned) -> list[S]:
        # This will panic at runtime :(
        # To make this work, we would need to replace the qubits in the struct
        # with `qubit | None` and write back `None` after `q1` has been extracted...
        foo(ss[0].q1, ss[0].q2)
        return ss

    validate(module.compile())


def test_nested_subscripts(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.declare(module)
    def foo(q: qubit) -> None: ...

    @guppy.declare(module)
    def bar(
        q1: qubit, q2: qubit, q3: qubit, q4: qubit
    ) -> None: ...

    @guppy(module)
    def main(qs: list[list[qubit]] @owned) -> list[list[qubit]]:
        foo(qs[0][0])
        # The following should work *without* panicking at runtime! Accessing `qs[0][0]`
        # replaces one qubit with `None` but puts everything back into `qs` before
        # going to the next argument.
        bar(qs[0][0], qs[0][1], qs[1][0], qs[1][1])
        return qs

    validate(module.compile())


def test_struct_nested_subscript(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.struct(module)
    class C:
        c: qubit
        blah: int

    @guppy.struct(module)
    class B:
        ys: list[list[C]]
        foo: C

    @guppy.struct(module)
    class A:
        xs: list[B]
        bar: qubit
        baz: tuple[B, B]

    @guppy.declare(module)
    def foo(q1: qubit) -> None: ...

    @guppy(module)
    def main(a: A @owned, i: int, j: int, k: int) -> A:
        foo(a.xs[i].ys[j][k].c)
        return a

    validate(module.compile())


def test_phase_gadget(validate):
    module = GuppyModule("test")
    module.load_all(quantum)
    module.load(angle)

    @guppy(module)
    def paulig(qs: list[qubit], alpha: angle) -> None:
        n = len(qs)
        for i in range(n - 1):
            cx(qs[i], qs[i + 1])
        rz(qs[n - 1], alpha)
        for i in range(n - 1):
            cx(qs[n - i - 1], qs[n - i - 2])

    validate(module.compile())
