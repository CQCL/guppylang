from collections.abc import Callable

from guppy.decorator import guppy
from guppy.module import GuppyModule


def test_id(validate):
    module = GuppyModule("test")
    T = guppy.type_var(module, "T")

    @guppy(module)
    def identity(x: T) -> T:
        return x

    validate(module.compile())


def test_nonlinear(validate):
    module = GuppyModule("test")
    T = guppy.type_var(module, "T")

    @guppy(module)
    def copy(x: T) -> tuple[T, T]:
        return x, x

    validate(module.compile())


def test_apply(validate):
    module = GuppyModule("test")
    S = guppy.type_var(module, "S")
    T = guppy.type_var(module, "T")

    @guppy(module)
    def apply(f: Callable[[S], T], x: S) -> T:
        return f(x)

    validate(module.compile())


def test_annotate(validate):
    module = GuppyModule("test")
    T = guppy.type_var(module, "T")

    @guppy(module)
    def identity(x: T) -> T:
        y: T = x
        return y

    validate(module.compile())


def test_recurse(validate):
    module = GuppyModule("test")
    T = guppy.type_var(module, "T")

    @guppy(module)
    def empty() -> T:
        return empty()

    validate(module.compile())


def test_call(validate):
    module = GuppyModule("test")
    T = guppy.type_var(module, "T")

    @guppy(module)
    def identity(x: T) -> T:
        return x

    @guppy(module)
    def main() -> float:
        return identity(5) + identity(42.0)

    validate(module.compile())
