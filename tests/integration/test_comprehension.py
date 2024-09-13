from hugr import tys

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import linst, owned
from guppylang.prelude.quantum import qubit
from guppylang.prelude.quantum_functional import h, cx

import guppylang.prelude.quantum as quantum
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

    @guppy(module)
    def test(qs: linst[qubit] @owned) -> linst[qubit]:
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

    @guppy.struct(module)
    class MyStruct:
        qs: linst[qubit]

    @guppy(module)
    def test(ss: linst[MyStruct] @owned) -> linst[qubit]:
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

    @guppy(module)
    def test(qs: linst[tuple[int, qubit, qubit]] @owned) -> linst[tuple[qubit, qubit]]:
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

    @guppy(module)
    def test(qs: linst[qubit] @owned) -> linst[qubit]:
        return [h(q) for q in [h(q) for q in qs]]

    validate(module.compile())


def test_classical_linst_comp(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy(module)
    def test(xs: list[int]) -> linst[int]:
        return [x for x in xs]

    validate(module.compile())


def test_linear_discard(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.declare(module)
    def discard(q: qubit @owned) -> None: ...

    @guppy(module)
    def test(qs: linst[qubit] @owned) -> list[None]:
        return [discard(q) for q in qs]

    validate(module.compile())


def test_linear_discard_struct(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.struct(module)
    class MyStruct:
        q1: qubit
        q2: qubit

    @guppy.declare(module)
    def discard(q1: qubit @owned, q2: qubit @owned) -> None: ...

    @guppy(module)
    def test(ss: linst[MyStruct] @owned) -> list[None]:
        return [discard(s.q1, s.q2) for s in ss]

    validate(module.compile())


def test_linear_consume_in_guard(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.declare(module)
    def cond(q: qubit @owned) -> bool: ...

    @guppy(module)
    def test(qs: linst[tuple[int, qubit]] @owned) -> list[int]:
        return [x for x, q in qs if cond(q)]

    validate(module.compile())


def test_linear_consume_in_iter(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.declare(module)
    def make_list(q: qubit @owned) -> list[int]: ...

    @guppy(module)
    def test(qs: linst[qubit] @owned) -> list[int]:
        return [x for q in qs for x in make_list(q)]

    validate(module.compile())


def test_linear_next_nonlinear_iter(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

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

    @guppy(module)
    def test(mt: MyType, xs: list[int]) -> linst[tuple[int, qubit]]:
        # We can use `mt` in an inner loop since it's not linear
        return [(x, q) for x in xs for q in mt]

    validate(module.compile())


def test_nonlinear_next_linear_iter(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.type(
        module,
        tys.Opaque(extension="prelude", id="qubit", args=[], bound=tys.TypeBound.Any),
        linear=True,
    )
    class MyIter:
        """A linear iterator that yields non-linear values."""

        @guppy.declare(module)
        def __hasnext__(self: "MyIter" @owned) -> tuple[bool, "MyIter"]: ...

        @guppy.declare(module)
        def __next__(self: "MyIter" @owned) -> tuple[int, "MyIter"]: ...

        @guppy.declare(module)
        def __end__(self: "MyIter" @owned) -> None: ...

    @guppy.type(module, NoneType().to_hugr())
    class MyType:
        """Type that produces the iterator above."""

        @guppy.declare(module)
        def __iter__(self: "MyType") -> MyIter: ...

    @guppy(module)
    def test(mt: MyType, xs: list[int]) -> linst[tuple[int, int]]:
        # We can use `mt` in an outer loop since the target `x` is not linear
        return [(x, x + y) for x in mt for y in xs]

    validate(module.compile())
