
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array, owned
from guppylang.std.quantum import qubit

import guppylang.std.quantum_functional as quantum
from tests.util import compile_guppy


def test_basic_exec(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy(module)
    def test() -> array[int, 10]:
        return array(i + 1 for i in range(10))

    @guppy(module)
    def main() -> int:
        s = 0
        for x in test():
            s += x
        return s

    package = module.compile()
    validate(package)
    run_int_fn(package, expected=sum(i + 1 for i in range(10)))


def test_basic_linear(validate):
    module = GuppyModule("test")
    module.load_all(quantum)
    module.load(qubit)

    @guppy(module)
    def test() -> array[qubit, 42]:
        return array(qubit() for _ in range(42))

    validate(module.compile())


def test_zero_length(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy(module)
    def test() -> array[float, 0]:
        return array(i / 0 for i in range(0))

    @guppy(module)
    def main() -> int:
        test()
        return 0

    package = module.compile()
    validate(package)
    run_int_fn(package, expected=0)


def test_capture(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy(module)
    def test(x: int) -> array[int, 42]:
        return array(i + x for i in range(42))

    @guppy(module)
    def main() -> int:
        s = 0
        for x in test(3):
            s += x
        return s

    package = module.compile()
    validate(package)
    run_int_fn(package, expected=sum(i + 3 for i in range(42)))


def test_capture_struct(validate):
    module = GuppyModule("test")

    @guppy.struct(module)
    class MyStruct:
        x: int
        y: float

    @guppy(module)
    def test(s: MyStruct) -> array[int, 42]:
        return array(i + s.x for i in range(42))

    validate(module.compile())


def test_scope(validate):
    @compile_guppy
    def test() -> float:
        x = 42.0
        array(x for x in range(10))
        return x

    validate(test)


def test_nested_left(validate, run_int_fn):
    module = GuppyModule("test")

    @guppy(module)
    def test() -> array[array[int, 10], 20]:
        return array(array(x + y for y in range(10)) for x in range(20))

    @guppy(module)
    def main() -> int:
        s = 0
        for xs in test():
            for x in xs:
                s += x
        return s

    package = module.compile()
    validate(package)
    run_int_fn(package, expected=sum(x + y for y in range(10) for x in range(20)))


def test_generic_size(validate):
    module = GuppyModule("test")
    n = guppy.nat_var("n", module)

    @guppy(module)
    def test(xs: array[int, n] @ owned) -> array[int, n]:
        return array(x + 1 for x in xs)

    validate(module.compile())


def test_generic_elem(validate):
    module = GuppyModule("test")
    T = guppy.type_var("T")

    @guppy(module)
    def foo(x: T) -> array[T, 10]:
        return array(x for _ in range(10))


def test_borrow(validate):
    module = GuppyModule("test")
    module.load_all(quantum)
    module.load(qubit)
    n = guppy.nat_var("n", module)

    @guppy.declare(module)
    def foo(q: qubit) -> int: ...

    @guppy(module)
    def test(q: qubit) -> array[int, n]:
        return array(foo(q) for _ in range(n))

    validate(module.compile())


def test_borrow_twice(validate):
    module = GuppyModule("test")
    module.load_all(quantum)
    module.load(qubit)
    n = guppy.nat_var("n", module)

    @guppy.declare(module)
    def foo(q: qubit) -> int: ...

    @guppy(module)
    def test(q: qubit) -> array[int, n]:
        return array(foo(q) + foo(q) for _ in range(n))

    validate(module.compile())


def test_borrow_struct(validate):
    module = GuppyModule("test")
    module.load_all(quantum)
    module.load(qubit)
    n = guppy.nat_var("n", module)

    @guppy.struct(module)
    class MyStruct:
        q1: qubit
        q2: qubit

    @guppy.declare(module)
    def foo(s: MyStruct) -> int: ...

    @guppy(module)
    def test(s: MyStruct) -> array[int, n]:
        return array(foo(s) for _ in range(n))

    validate(module.compile())


def test_borrow_and_consume(validate):
    module = GuppyModule("test")
    module.load_all(quantum)
    module.load(qubit)
    n = guppy.nat_var("n", module)

    @guppy.declare(module)
    def foo(q: qubit) -> int: ...

    @guppy.declare(module)
    def bar(q: qubit @ owned) -> int: ...

    @guppy(module)
    def test(qs: array[qubit, n] @ owned) -> array[int, n]:
        return array(foo(q) + bar(q) for q in qs)

    validate(module.compile())

