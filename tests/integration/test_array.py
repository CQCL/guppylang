import pytest

from hugr import ops
from hugr.std.int import IntVal

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array, owned, mem_swap, nat
from tests.util import compile_guppy

from guppylang.std.quantum import qubit, discard
import guppylang.std.quantum as quantum


@pytest.mark.skip("Requires `is_to_u` in llvm")
def test_len_execute(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy(module)
    def main(xs: array[float, 42]) -> int:
        return len(xs)

    compiled = module.compile()
    validate(compiled)
    if run_int_fn is not None:
        run_int_fn(compiled, 42)


def test_len(validate):
    test_len_execute(validate, None)


def test_len_linear(validate):
    module = GuppyModule("test")
    module.load(qubit)

    @guppy(module)
    def main(qs: array[qubit, 42]) -> int:
        return len(qs)

    validate(module.compile())


def test_len_generic(validate):
    module = GuppyModule("test")

    n = guppy.nat_var("n", module=module)

    @guppy(module)
    def main(qs: array[bool, n]) -> bool:
        for i in range(len(qs)):
            if qs[i]:
                return True
        return False

    package = module.compile()
    validate(package)

    hg = package.module
    load_nats = [
        data.op
        for _, data in hg.nodes()
        if isinstance(data.op, ops.ExtOp) and data.op.op_def().name == "load_nat"
    ]
    assert len(load_nats) == 1


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
    def main(qs: array[qubit, 42] @ owned, i: int) -> array[qubit, 42]:
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
    def main(qs: array[qubit, 42] @ owned) -> array[qubit, 42]:
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
    def main(ss: array[S, 10] @ owned) -> array[S, 10]:
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
    def bar(q1: qubit, q2: qubit, q3: qubit, q4: qubit) -> None: ...

    @guppy(module)
    def main(qs: array[array[qubit, 13], 42] @ owned) -> array[array[qubit, 13], 42]:
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
    def main(a: A @ owned, i: int, j: int, k: int) -> A:
        foo(a.xs[i].ys[j][k].c)
        return a

    validate(module.compile())


def test_generic_function(validate):
    module = GuppyModule("test")
    module.load(qubit)
    T = guppy.type_var("T", copyable=False, droppable=False, module=module)
    n = guppy.nat_var("n", module=module)

    @guppy(module)
    def foo(xs: array[T, n] @ owned) -> array[T, n]:
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
        a = array(1, 2, 3)
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
        return xs[0] + ys[0]  # Check copy isn't modified

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
        return xs[0] + ys[0]  # Check copy isn't modified

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=5)


def test_copy3(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy(module)
    def main() -> int:
        xs = array(1, 2, 3)
        ys = copy(xs)
        return xs[0]  # Check original can keep being used

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=1)


def test_copy_struct(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy.struct(module)
    class S:
        a: array[int, 1]

    @guppy(module)
    def main() -> int:
        xs = array(S(array(1)), S(array(2)))
        ys = copy(xs[0].a)
        return ys[0]

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=1)


def test_copy_const(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy(module)
    def main() -> int:
        xs = copy(array(1, 2, 3))
        return xs[0]

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=1)


def test_subscript_assign(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy(module)
    def foo(xs: array[int, 3] @ owned, idx: int, n: int) -> array[int, 3]:
        xs[idx] = n
        return xs

    @guppy(module)
    def main() -> int:
        xs = array(0, 0, 0)
        xs = foo(xs, 0, 2)
        return xs[0]

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=2)


def test_subscript_assign_add(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy(module)
    def foo(xs: array[int, 1], n: int) -> None:
        xs[0] += n

    @guppy(module)
    def main() -> int:
        xs = array(0)
        for i in range(6):
            foo(xs, i)
        return xs[0]

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=15)


def test_subscript_assign_struct(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy.struct(module)
    class S:
        a: array[int, 2]

    @guppy(module)
    def foo(xs: array[int, 2], idx: int, n: int) -> None:
        xs[idx] = n

    @guppy(module)
    def main() -> int:
        s = S(array(0, 0))
        foo(s.a, 1, 42)
        return s.a[1]

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=42)


def test_subscript_assign_nested(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy(module)
    def foo(xs: array[array[int, 2], 2]) -> None:
        xs[0][0] = 22

    @guppy(module)
    def main() -> int:
        xs = array(array(11, 11), array(11, 11))
        foo(xs)
        return xs[0][0]

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=22)


def test_subscript_assign_nested_struct1(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy.struct(module)
    class S:
        a: array[int, 2]

    @guppy(module)
    def main() -> int:
        s0 = S(array(0, 0))
        s1 = S(array(1, 1))
        arr = array(s0, s1)
        arr[0].a[1] = 42
        return arr[0].a[1]

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=42)


def test_subscript_assign_nested_struct2(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy.struct(module)
    class A:
        b: array[int, 2]

    @guppy.struct(module)
    class S:
        a: array[A, 2]

    @guppy(module)
    def main() -> int:
        s0 = S(array(A(array(0, 0)), A(array(0, 0))))
        s1 = S(array(A(array(0, 0)), A(array(0, 0))))
        arr = array(s0, s1)
        arr[0].a[1].b = array(42, 42)
        arr[0].a[1].b[0] = 43
        return arr[0].a[1].b[0]

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=43)


def test_subscript_assign_nested_struct3(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy.struct(module)
    class A:
        b: array[int, 2]

    @guppy.struct(module)
    class S:
        a: A

    @guppy(module)
    def main() -> int:
        s0 = S(A(array(0, 0)))
        s1 = S(A(array(0, 0)))
        arr = array(s0, s1)
        arr[0].a.b[0] = 2
        return arr[0].a.b[0]

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=2)


def test_subscript_assign_nested_struct4(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy.struct(module)
    class S:
        xs: array[int, 1]

    @guppy(module)
    def main() -> int:
        arr = array(S(array(0)), S(array(1)))
        arr[0].xs = array(3)
        return arr[0].xs[0]

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=3)


def test_subscript_assign_nested_struct5(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy.struct(module)
    class A:
        b: array[int, 2]

    @guppy.struct(module)
    class S:
        a: array[A, 2]

    @guppy(module)
    def main() -> int:
        s0 = S(array(A(array(0, 0)), A(array(0, 0))))
        s1 = S(array(A(array(0, 0)), A(array(0, 0))))
        arr = array(s0, s1)
        arr[0].a[0].b = array(42, 42)
        return arr[0].a[0].b[0]

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=42)


def test_subscript_assign_unpacking(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy(module)
    def main() -> int:
        xs = array(11, 22, 33)
        xs[0], y = 44, 55
        return xs[0]

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=44)


def test_subscript_subscript_assign(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy(module)
    def main() -> int:
        xs = array(0)
        ys = array(1)
        xs[0] = ys[0]
        return xs[0]

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=1)


def test_subscript_assign_unpacking_tuple(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy(module)
    def main() -> int:
        xs = array(0, 0, 0)
        a, *b, xs[1] = (1, 2, 3, 4)
        return xs[1]

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=4)


def test_subscript_assign_unpacking_complicated(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy(module)
    def main() -> int:
        xs = array(0, 0, 0)
        (a1, a2), *b, (c1, c2) = array((0, 1), (2, 3), (4, 5), (5, 6))
        return a1 + c1

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=5)


def test_subscript_assign_unpacking_range(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy(module)
    def main() -> int:
        xs = array(0, 0, 0)
        a, *b, xs[1] = range(10)
        return xs[1]

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=9)


def test_subscript_assign_unpacking_array(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy(module)
    def main() -> int:
        xs = array(0, 0, 0)
        a, *b, xs[1] = array(1, 2, 3, 4)
        return xs[1]

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=4)


# Verifies that array.__getitem__ works across multiple functions calls.
def test_multiple_functions(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy(module)
    def first(arr: array[int, 2]) -> int:
        return arr[0]

    @guppy(module)
    def second(arr: array[int, 2]) -> int:
        return arr[1]

    @guppy(module)
    def main() -> int:
        xs = array(1, 2)
        return first(xs) + second(xs)

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=3)


def test_assign_dataflow(validate):
    """Test that dataflow analysis considers subscript assignments as uses and correctly
    wires up the Hugr.

    See https://github.com/CQCL/guppylang/issues/844
    """
    module = GuppyModule("test")

    @guppy(module)
    def test1() -> None:
        xs = array(1, 2)
        for i in range(2):
            xs[i] = 0

    @guppy(module)
    def test2() -> None:
        xs = array(0, 1)
        ys = array(1, 2)
        for i in range(2):
            ys[xs[i]] = 0

    module.compile()
