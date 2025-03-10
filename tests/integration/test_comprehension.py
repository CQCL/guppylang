from hugr import tys

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import owned
from guppylang.std.option import Option
from guppylang.std.quantum import qubit
from guppylang.std.quantum_functional import h, cx

import guppylang.std.quantum_functional as quantum
from guppylang.tys.ty import NoneType
from tests.util import compile_guppy


def test_basic(validate):
    @compile_guppy
    def test(xs: list[float]) -> list[int]:
        return [int(x) for x in xs]

    validate(test)


def test_basic_linear(validate):
    module = GuppyModule("test")
    module.load_all(quantum)
    module.load(qubit)

    @guppy(module)
    def test(qs: list[qubit] @owned) -> list[qubit]:
        return [h(q) for q in qs]

    validate(module.compile())


def test_guarded(validate):
    @compile_guppy
    def test(xs: list[int]) -> list[int]:
        return [2 * x for x in xs if x > 0 if x < 20]

    validate(test)


def test_multiple(validate):
    @compile_guppy
    def test(xs: list[int], ys: list[int]) -> list[int]:
        return [x + y for x in xs for y in ys if x + y > 42]

    validate(test)


def test_multiple_struct(validate):
    module = GuppyModule("test")
    module.load_all(quantum)
    module.load(qubit)

    @guppy.struct(module)
    class MyStruct:
        qs: list[qubit]

    @guppy(module)
    def test(ss: list[MyStruct] @owned) -> list[qubit]:
        return [h(q) for s in ss for q in s.qs]

    validate(module.compile())


def test_tuple_pat(validate):
    @compile_guppy
    def test(xs: list[tuple[int, int, float]]) -> list[float]:
        return [x + y * z for x, y, z in xs if x - y > z]

    validate(test)


def test_tuple_pat_linear(validate):
    module = GuppyModule("test")
    module.load_all(quantum)
    module.load(qubit)

    @guppy(module)
    def test(qs: list[tuple[int, qubit, qubit]] @owned) -> list[tuple[qubit, qubit]]:
        return [cx(q1, q2) for _, q1, q2 in qs]

    validate(module.compile())


def test_tuple_return(validate):
    @compile_guppy
    def test(xs: list[int], ys: list[float]) -> list[tuple[int, float]]:
        return [(x, y) for x in xs for y in ys]

    validate(test)


def test_dependent(validate):
    module = GuppyModule("test")

    @guppy.declare(module)
    def process(x: float) -> list[int]: ...

    @guppy(module)
    def test(xs: list[float]) -> list[float]:
        return [x * y for x in xs if x > 0 for y in process(x) if y > x]

    validate(module.compile())


def test_capture(validate):
    @compile_guppy
    def test(xs: list[int], y: int) -> list[int]:
        return [x + y for x in xs if x > y]

    validate(test)


def test_capture_struct(validate):
    module = GuppyModule("test")

    @guppy.struct(module)
    class MyStruct:
        x: int
        y: float

    @guppy(module)
    def test(xs: list[int], s: MyStruct) -> list[int]:
        return [x + s.x for x in xs if x > s.y]

    validate(module.compile())


def test_scope(validate):
    @compile_guppy
    def test(xs: list[None]) -> float:
        x = 42.0
        [x for x in xs]
        return x

    validate(test)


def test_nested_left(validate):
    @compile_guppy
    def test(xs: list[int], ys: list[float]) -> list[list[float]]:
        return [[x + y for y in ys] for x in xs]

    validate(test)


def test_nested_right(validate):
    @compile_guppy
    def test(xs: list[int]) -> list[int]:
        return [-x for x in [2 * x for x in xs]]

    validate(test)


def test_nested_linear(validate):
    module = GuppyModule("test")
    module.load_all(quantum)
    module.load(qubit)

    @guppy(module)
    def test(qs: list[qubit] @owned) -> list[qubit]:
        return [h(q) for q in [h(q) for q in qs]]

    validate(module.compile())


def test_classical_list_comp(validate):
    module = GuppyModule("test")
    module.load_all(quantum)
    module.load(qubit)

    @guppy(module)
    def test(xs: list[int]) -> list[int]:
        return [x for x in xs]

    validate(module.compile())


def test_linear_discard(validate):
    module = GuppyModule("test")
    module.load_all(quantum)
    module.load(qubit)

    @guppy.declare(module)
    def discard(q: qubit @owned) -> None: ...

    @guppy(module)
    def test(qs: list[qubit] @owned) -> list[None]:
        return [discard(q) for q in qs]

    validate(module.compile())


def test_linear_discard_struct(validate):
    module = GuppyModule("test")
    module.load_all(quantum)
    module.load(qubit)

    @guppy.struct(module)
    class MyStruct:
        q1: qubit
        q2: qubit

    @guppy.declare(module)
    def discard(q1: qubit @owned, q2: qubit @owned) -> None: ...

    @guppy(module)
    def test(ss: list[MyStruct] @owned) -> list[None]:
        return [discard(s.q1, s.q2) for s in ss]

    validate(module.compile())


def test_linear_consume_in_guard(validate):
    module = GuppyModule("test")
    module.load_all(quantum)
    module.load(qubit)

    @guppy.declare(module)
    def cond(q: qubit @owned) -> bool: ...

    @guppy(module)
    def test(qs: list[tuple[int, qubit]] @owned) -> list[int]:
        return [x for x, q in qs if cond(q)]

    validate(module.compile())


def test_linear_consume_in_iter(validate):
    module = GuppyModule("test")
    module.load_all(quantum)
    module.load(qubit)

    @guppy.declare(module)
    def make_list(q: qubit @owned) -> list[int]: ...

    @guppy(module)
    def test(qs: list[qubit] @owned) -> list[int]:
        return [x for q in qs for x in make_list(q)]

    validate(module.compile())


def test_linear_next_nonlinear_iter(validate):
    module = GuppyModule("test")
    module.load_all(quantum)
    module.load(qubit)

    @guppy.type(NoneType().to_hugr(), module=module)
    class MyIter:
        """An iterator that yields linear values but is not linear itself."""

        @guppy.declare(module)
        def __next__(self: "MyIter") -> Option[tuple[qubit, "MyIter"]]: ...

    @guppy.type(NoneType().to_hugr(), module=module)
    class MyType:
        """Type that produces the iterator above."""

        @guppy.declare(module)
        def __iter__(self: "MyType") -> MyIter: ...

    @guppy(module)
    def test(mt: MyType, xs: list[int]) -> list[tuple[int, qubit]]:
        # We can use `mt` in an inner loop since it's not linear
        return [(x, q) for x in xs for q in mt]

    validate(module.compile())


def test_nonlinear_next_linear_iter(validate):
    module = GuppyModule("test")
    module.load_all(quantum)
    module.load(qubit)

    @guppy.type(
        tys.Opaque(extension="prelude", id="qubit", args=[], bound=tys.TypeBound.Any),
        copyable=False,
        droppable=False,
        module=module,
    )
    class MyIter:
        """A linear iterator that yields non-linear values."""

        @guppy.declare(module)
        def __next__(self: "MyIter" @owned) -> Option[tuple[int, "MyIter"]]: ...

    @guppy.type(NoneType().to_hugr(), module=module)
    class MyType:
        """Type that produces the iterator above."""

        @guppy.declare(module)
        def __iter__(self: "MyType") -> MyIter: ...

    @guppy(module)
    def test(mt: MyType, xs: list[int]) -> list[tuple[int, int]]:
        # We can use `mt` in an outer loop since the target `x` is not linear
        return [(x, x + y) for x in mt for y in xs]

    validate(module.compile())


def test_borrow(validate):
    module = GuppyModule("test")
    module.load_all(quantum)
    module.load(qubit)

    @guppy.declare(module)
    def foo(q: qubit) -> int: ...

    @guppy(module)
    def test(q: qubit, n: int) -> list[int]:
        return [foo(q) for _ in range(n)]

    validate(module.compile())


def test_borrow_nested(validate):
    module = GuppyModule("test")
    module.load_all(quantum)
    module.load(qubit)

    @guppy.declare(module)
    def foo(q: qubit) -> int: ...

    @guppy(module)
    def test(q: qubit, n: int, m: int) -> list[int]:
        return [foo(q) for _ in range(n) for _ in range(m)]

    validate(module.compile())


def test_borrow_guarded(validate):
    module = GuppyModule("test")
    module.load_all(quantum)
    module.load(qubit)

    @guppy.declare(module)
    def foo(q: qubit) -> int: ...

    @guppy(module)
    def test(q: qubit, n: int) -> list[int]:
        return [foo(q) for i in range(n) if i % 2 == 0]

    validate(module.compile())


def test_borrow_twice(validate):
    module = GuppyModule("test")
    module.load_all(quantum)
    module.load(qubit)

    @guppy.declare(module)
    def foo(q: qubit) -> int: ...

    @guppy(module)
    def test(q: qubit, n: int) -> list[int]:
        return [foo(q) + foo(q) for _ in range(n)]

    validate(module.compile())


def test_borrow_in_guard(validate):
    module = GuppyModule("test")
    module.load_all(quantum)
    module.load(qubit)

    @guppy.declare(module)
    def foo(q: qubit) -> int: ...

    @guppy.declare(module)
    def bar(q: qubit) -> bool: ...

    @guppy(module)
    def test(q: qubit, n: int) -> list[int]:
        return [foo(q) for _ in range(n) if bar(q)]

    validate(module.compile())


def test_borrow_in_iter(validate):
    module = GuppyModule("test")
    module.load_all(quantum)
    module.load(qubit)

    @guppy.declare(module)
    def foo(q: qubit) -> int: ...

    @guppy(module)
    def test(q: qubit @ owned) -> tuple[list[int], qubit]:
        return [foo(q) for _ in range(foo(q))], q

    validate(module.compile())


def test_borrow_struct(validate):
    module = GuppyModule("test")
    module.load_all(quantum)
    module.load(qubit)

    @guppy.struct(module)
    class MyStruct:
        q1: qubit
        q2: qubit

    @guppy.declare(module)
    def foo(s: MyStruct) -> int: ...

    @guppy(module)
    def test(s: MyStruct, n: int) -> list[int]:
        return [foo(s) for _ in range(n)]

    validate(module.compile())


def test_borrow_and_consume(validate):
    module = GuppyModule("test")
    module.load_all(quantum)
    module.load(qubit)

    @guppy.declare(module)
    def foo(q: qubit) -> int: ...

    @guppy.declare(module)
    def bar(q: qubit @ owned) -> int: ...

    @guppy(module)
    def test(qs: list[qubit] @ owned) -> list[int]:
        return [foo(q) + bar(q) for q in qs]

    validate(module.compile())


