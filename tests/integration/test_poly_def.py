from collections.abc import Callable

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array, owned


def test_id(validate):
    module = GuppyModule("test")
    T = guppy.type_var("T", module=module)

    @guppy(module)
    def identity(x: T) -> T:
        return x

    validate(module.compile())


def test_nonlinear(validate):
    module = GuppyModule("test")
    T = guppy.type_var("T", module=module)

    @guppy(module)
    def copy(x: T) -> tuple[T, T]:
        return x, x

    validate(module.compile())


def test_apply(validate):
    module = GuppyModule("test")
    S = guppy.type_var("S", module=module)
    T = guppy.type_var("T", module=module)

    @guppy(module)
    def apply(f: Callable[[S], T], x: S) -> T:
        return f(x)

    validate(module.compile())


def test_annotate(validate):
    module = GuppyModule("test")
    T = guppy.type_var("T", module=module)

    @guppy(module)
    def identity(x: T) -> T:
        y: T = x
        return y

    validate(module.compile())


def test_recurse(validate):
    module = GuppyModule("test")
    T = guppy.type_var("T", module=module)

    @guppy(module)
    def empty() -> T:
        return empty()

    validate(module.compile())


def test_call(validate):
    module = GuppyModule("test")
    T = guppy.type_var("T", module=module)

    @guppy(module)
    def identity(x: T) -> T:
        return x

    @guppy(module)
    def main() -> float:
        return identity(5) + identity(42.0)

    validate(module.compile())


def test_nat(validate):
    module = GuppyModule("test")
    T = guppy.type_var("T", module=module)
    n = guppy.nat_var("n", module=module)

    @guppy(module)
    def foo(xs: array[T, n] @ owned) -> array[T, n]:
        return xs

    validate(module.compile())


def test_nat_use(validate):
    module = GuppyModule("test")
    n = guppy.nat_var("n", module=module)

    @guppy(module)
    def foo(xs: array[int, n]) -> int:
        return int(n)

    validate(module.compile())


def test_nat_call(validate):
    module = GuppyModule("test")
    T = guppy.type_var("T", module=module)
    n = guppy.nat_var("n", module=module)

    @guppy(module)
    def foo() -> array[T, n]:
        return foo()

    @guppy(module)
    def main() -> tuple[array[int, 10], array[float, 20]]:
        return foo(), foo()

    validate(module.compile())


def test_nat_recurse(validate):
    module = GuppyModule("test")
    n = guppy.nat_var("n", module=module)

    @guppy(module)
    def empty() -> array[int, n]:
        return empty()

    validate(module.compile())


def test_type_apply(validate):
    module = GuppyModule("test")
    T = guppy.type_var("T", module=module)
    n = guppy.nat_var("n", module=module)

    @guppy.declare(module)
    def foo(x: array[T, n]) -> array[T, n]: ...

    @guppy(module)
    def identity(x: array[T, n]) -> array[T, n]:
        return foo[T, n](x)

    validate(module.compile())

