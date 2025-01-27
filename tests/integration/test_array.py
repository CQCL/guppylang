from hugr import ops
from hugr.std.int import IntVal

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array, owned, mem_swap
from tests.util import compile_guppy

from guppylang.std.quantum import qubit, discard
import guppylang.std.quantum as quantum


def test_len(validate):
    module = GuppyModule("test")

    @guppy(module)
    def main(xs: array[float, 42]) -> int:
        return len(xs)

    package = module.compile()
    validate(package)

    hg = package.module
    [val] = [data.op for node, data in hg.nodes() if isinstance(data.op, ops.Const)]
    assert isinstance(val, ops.Const)
    assert isinstance(val.val, IntVal)
    assert val.val.v == 42


def test_len_linear(validate):
    module = GuppyModule("test")
    module.load(qubit)

    @guppy(module)
    def main(qs: array[qubit, 42]) -> int:
        return len(qs)

    package = module.compile()
    validate(package)

    hg = package.module
    [val] = [data.op for node, data in hg.nodes() if isinstance(data.op, ops.Const)]
    assert isinstance(val, ops.Const)
    assert isinstance(val.val, IntVal)
    assert val.val.v == 42


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
    def main(ys: array[int, 0] @ owned) -> array[array[int, 0], 2]:
        xs = array(ys, array())
        return xs

    validate(main)


def test_return_linear_array(validate):
    module = GuppyModule("test")
    module.load(qubit)

    @guppy(module)
    def foo() -> array[qubit, 2]:
        a = array(qubit(), qubit())
        return a

    validate(module.compile())


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
    def foo(q: qubit) -> None: ...

    @guppy(module)
    def main(qs: array[qubit, 42] @owned, i: int) -> array[qubit, 42]:
        foo(qs[i])
        return qs

    validate(module.compile())


def test_inout_subscript(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.declare(module)
    def foo(q: qubit) -> None: ...

    @guppy(module)
    def main(qs: array[qubit, 42], i: int) -> None:
        foo(qs[i])

    validate(module.compile())


def test_multi_subscripts(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.declare(module)
    def foo(q1: qubit, q2: qubit) -> None: ...

    @guppy(module)
    def main(qs: array[qubit, 42] @owned) -> array[qubit, 42]:
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
    def foo(q1: qubit, q2: qubit) -> None: ...

    @guppy(module)
    def main(ss: array[S, 10] @owned) -> array[S, 10]:
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
    def main(qs: array[array[qubit, 13], 42] @owned) -> array[array[qubit, 13], 42]:
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
    def foo(q1: qubit) -> None: ...

    @guppy(module)
    def main(a: A @owned, i: int, j: int, k: int) -> A:
        foo(a.xs[i].ys[j][k].c)
        return a

    validate(module.compile())


def test_generic_function(validate):
    module = GuppyModule("test")
    module.load(qubit)
    T = guppy.type_var("T", copyable=False, droppable=False, module=module)
    n = guppy.nat_var("n", module=module)

    @guppy(module)
    def foo(xs: array[T, n] @owned) -> array[T, n]:
        return xs

    @guppy(module)
    def main() -> tuple[array[int, 3], array[qubit, 2]]:
        xs = array(1, 2, 3)
        ys = array(qubit(), qubit())
        return foo(xs), foo(ys)

    validate(module.compile())


def test_linear_for_loop(validate):
    module = GuppyModule("test")
    module.load(qubit, discard)

    @guppy(module)
    def main() -> None:
        qs = array(qubit(), qubit(), qubit())
        for q in qs:
            discard(q)

    validate(module.compile())


def test_exec_array(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy(module)
    def main() -> int:
        a = array(1,2,3)
        return a[0] + a[1] + a[2]

    package = module.compile()
    validate(package)
    run_int_fn(package, expected=6)


def test_exec_array_loop(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy(module)
    def main() -> int:
        xs = array(1, 2, 3, 4, 5, 6, 7)
        s = 0
        for x in xs:
            if x % 2 == 0:
                continue
            if x > 5:
                break
            s += x
        return s

    package = module.compile()
    validate(package)

    run_int_fn(package, expected=9)


def test_mem_swap(validate):
    module = GuppyModule("test")

    module.load(qubit)
    @guppy(module)
    def foo(x: qubit, y: qubit) -> None:
        mem_swap(x, y)

    @guppy(module)
    def main() -> array[qubit, 2]:
        a = array(qubit(), qubit())
        foo(a[0], a[1])
        return a

    package = module.compile()
    validate(package)


def test_drop(validate):
    @compile_guppy
    def main(xs: array[int, 2] @ owned) -> None:
        ys = xs

    validate(main)


def test_copy1(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy(module)
    def main() -> int:
        xs = array(1, 2, 3)
        ys = xs.copy()
        xs = array(4, 5, 6) 
        return xs[0] + ys[0] # Check copy isn't modified

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=5)


def test_copy2(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy(module)
    def main() -> int:
        xs = array(1, 2, 3)
        ys = copy(xs)
        xs = array(4, 5, 6) 
        return xs[0] + ys[0] # Check copy isn't modified

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=5)


def test_copy3(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy(module)
    def main() -> int:
        xs = array(1, 2, 3)
        ys = copy(xs)
        return xs[0] # Check original can keep being used

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=4)

