from collections.abc import Callable

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import qubit

import guppylang.prelude.quantum as quantum


def test_id(validate):
    module = GuppyModule("test")
    T = guppy.type_var(module, "T")

    @guppy.declare(module)
    def foo(x: T) -> T: ...

    @guppy(module)
    def main(x: int) -> int:
        return foo(x)

    validate(module.compile())


def test_id_nested(validate):
    module = GuppyModule("test")
    T = guppy.type_var(module, "T")

    @guppy.declare(module)
    def foo(x: T) -> T: ...

    @guppy(module)
    def main(x: int) -> int:
        return foo(foo(foo(x)))

    validate(module.compile())


def test_use_twice(validate):
    module = GuppyModule("test")
    T = guppy.type_var(module, "T")

    @guppy.declare(module)
    def foo(x: T) -> T: ...

    @guppy(module)
    def main(x: int, y: bool) -> None:
        foo(x)
        foo(y)

    validate(module.compile())


def test_define_twice(validate):
    module = GuppyModule("test")
    T = guppy.type_var(module, "T")

    @guppy.declare(module)
    def foo(x: T) -> T: ...

    @guppy.declare(module)
    def bar(x: T) -> T:  # Reuse same type var!
        ...

    @guppy(module)
    def main(x: bool, y: float) -> None:
        foo(x)
        foo(y)

    validate(module.compile())


def test_return_tuple_implicit(validate):
    module = GuppyModule("test")
    T = guppy.type_var(module, "T")

    @guppy.declare(module)
    def foo(x: T) -> T: ...

    @guppy(module)
    def main(x: int) -> tuple[int, int]:
        return foo((x, 0))

    validate(module.compile())


def test_same_args(validate):
    module = GuppyModule("test")
    T = guppy.type_var(module, "T")

    @guppy.declare(module)
    def foo(x: T, y: T) -> None: ...

    @guppy(module)
    def main(x: int) -> None:
        foo(x, 42)

    validate(module.compile())


def test_different_args(validate):
    module = GuppyModule("test")
    S = guppy.type_var(module, "S")
    T = guppy.type_var(module, "T")

    @guppy.declare(module)
    def foo(x: S, y: T, z: tuple[S, T]) -> T: ...

    @guppy(module)
    def main(x: int, y: float) -> float:
        return foo(x, y, (x, y)) + foo(y, 42.0, (0.0, y))

    validate(module.compile())


def test_infer_basic(validate):
    module = GuppyModule("test")
    T = guppy.type_var(module, "T")

    @guppy.declare(module)
    def foo() -> T: ...

    @guppy(module)
    def main() -> None:
        x: int = foo()

    validate(module.compile())


def test_infer_list(validate):
    module = GuppyModule("test")
    T = guppy.type_var(module, "T")

    @guppy.declare(module)
    def foo() -> T: ...

    @guppy(module)
    def main() -> None:
        xs: list[int] = [foo()]
        ys = [1.0, foo()]

    validate(module.compile())


def test_infer_nested(validate):
    module = GuppyModule("test")
    T = guppy.type_var(module, "T")

    @guppy.declare(module)
    def foo() -> T: ...

    @guppy.declare(module)
    def bar(x: T) -> T: ...

    @guppy(module)
    def main() -> None:
        x: int = bar(foo())

    validate(module.compile())


def test_infer_left_to_right(validate):
    module = GuppyModule("test")
    S = guppy.type_var(module, "S")
    T = guppy.type_var(module, "T")

    @guppy.declare(module)
    def foo() -> T: ...

    @guppy.declare(module)
    def bar(x: T, y: T, z: S, a: tuple[T, S]) -> None: ...

    @guppy(module)
    def main() -> None:
        bar(42, foo(), False, foo())

    validate(module.compile())


def test_pass_poly_basic(validate):
    module = GuppyModule("test")
    T = guppy.type_var(module, "T")

    @guppy.declare(module)
    def foo(f: Callable[[T], T]) -> None: ...

    @guppy.declare(module)
    def bar(x: int) -> int: ...

    @guppy(module)
    def main() -> None:
        foo(bar)

    validate(module.compile())


def test_pass_poly_cross(validate):
    module = GuppyModule("test")
    S = guppy.type_var(module, "S")
    T = guppy.type_var(module, "T")

    @guppy.declare(module)
    def foo(f: Callable[[S], int]) -> None: ...

    @guppy.declare(module)
    def bar(x: bool) -> T: ...

    @guppy(module)
    def main() -> None:
        foo(bar)

    validate(module.compile())


def test_linear(validate):
    module = GuppyModule("test")
    module.load(quantum)
    T = guppy.type_var(module, "T", linear=True)

    @guppy.declare(module)
    def foo(x: T) -> T: ...

    @guppy(module)
    def main(q: qubit) -> qubit:
        return foo(q)

    validate(module.compile())


def test_pass_nonlinear(validate):
    module = GuppyModule("test")
    module.load(quantum)
    T = guppy.type_var(module, "T", linear=True)

    @guppy.declare(module)
    def foo(x: T) -> T: ...

    @guppy(module)
    def main(x: int) -> None:
        foo(x)

    validate(module.compile())


def test_pass_linear(validate):
    module = GuppyModule("test")
    module.load(quantum)
    T = guppy.type_var(module, "T", linear=True)

    @guppy.declare(module)
    def foo(f: Callable[[T], T]) -> None: ...

    @guppy.declare(module)
    def bar(q: qubit) -> qubit: ...

    @guppy(module)
    def main() -> None:
        foo(bar)

    validate(module.compile())


def test_higher_order_value(validate):
    module = GuppyModule("test")
    T = guppy.type_var(module, "T")

    @guppy.declare(module)
    def foo(x: T) -> T: ...

    @guppy.declare(module)
    def bar(x: T) -> T: ...

    @guppy(module)
    def main(b: bool) -> int:
        f = foo if b else bar
        return f(42)

    validate(module.compile())
