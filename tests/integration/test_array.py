import pytest
from hugr import ops
from hugr.std.int import IntVal

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import array, inout
from tests.util import compile_guppy

from guppylang.prelude.quantum import qubit
import guppylang.prelude.quantum as quantum


@pytest.mark.xfail(reason="hugr-includes-whole-stdlib")
def test_len(validate):
    module = GuppyModule("test")

    @guppy(module)
    def main(xs: array[float, 42]) -> int:
        return len(xs)

    hg = module.compile()
    validate(hg)

    [val] = [data.op for node, data in hg.nodes() if isinstance(data.op, ops.Const)]
    assert isinstance(val, ops.Const)
    assert isinstance(val.val, IntVal)
    assert val.val.v == 42


@pytest.mark.skip("Skipped until Hugr lowering is updated")
def test_index(validate):
    @compile_guppy
    def main(xs: array[int, 5], i: int) -> int:
        return xs[0] + xs[i] + xs[xs[2 * i]]

    validate(main)


def test_new_array(validate):
    @compile_guppy
    def main(x: int, y: int) -> array[int, 3]:
        xs = array(x, y, x)
        return xs

    validate(main)


def test_new_array_infer_empty(validate):
    @compile_guppy
    def main() -> array[float, 0]:
        return array()

    validate(main)


def test_new_array_infer_nested(validate):
    @compile_guppy
    def main(ys: array[int, 0]) -> array[array[int, 0], 2]:
        xs = array(ys, array())
        return xs

    validate(main)


def test_subscript_drop_rest(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.declare(module)
    def foo() -> array[int, 10]: ...

    @guppy(module)
    def main() -> int:
        return foo()[0]

    validate(module.compile())


def test_linear_subscript(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.declare(module)
    def foo(q: qubit @inout) -> None: ...

    @guppy(module)
    def main(qs: array[qubit, 42], i: int) -> array[qubit, 42]:
        foo(qs[i])
        return qs

    validate(module.compile())


def test_inout_subscript(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.declare(module)
    def foo(q: qubit @inout) -> None: ...

    @guppy(module)
    def main(qs: array[qubit, 42] @inout, i: int) -> None:
        foo(qs[i])

    validate(module.compile())


def test_multi_subscripts(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.declare(module)
    def foo(q1: qubit @inout, q2: qubit @inout) -> None: ...

    @guppy(module)
    def main(qs: array[qubit, 42]) -> array[qubit, 42]:
        foo(qs[0], qs[1])
        foo(qs[0], qs[0])  # Will panic at runtime
        return qs

    validate(module.compile())


def test_struct_array(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.struct(module)
    class S:
        q1: qubit
        q2: qubit

    @guppy.declare(module)
    def foo(q1: qubit @inout, q2: qubit @inout) -> None: ...

    @guppy(module)
    def main(ss: array[S, 10]) -> array[S, 10]:
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
    def foo(q: qubit @inout) -> None: ...

    @guppy.declare(module)
    def bar(
        q1: qubit @inout, q2: qubit @inout, q3: qubit @inout, q4: qubit @inout
    ) -> None: ...

    @guppy(module)
    def main(qs: array[array[qubit, 13], 42]) -> array[array[qubit, 13], 42]:
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
        ys: array[array[C, 10], 20]
        foo: C

    @guppy.struct(module)
    class A:
        xs: array[B, 42]
        bar: qubit
        baz: tuple[B, B]

    @guppy.declare(module)
    def foo(q1: qubit @inout) -> None: ...

    @guppy(module)
    def main(a: A, i: int, j: int, k: int) -> A:
        foo(a.xs[i].ys[j][k].c)
        return a

    validate(module.compile())
