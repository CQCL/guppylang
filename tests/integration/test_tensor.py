# ruff: noqa: F821
# ^ Stop ruff complaining about not knowing what "tensor" is

from collections.abc import Callable

from guppylang.decorator import guppy
from guppylang.module import GuppyModule


def test_singleton(validate):
    module = GuppyModule("module")

    @guppy(module)
    def foo(x: int) -> bool:
        return x == 42

    @guppy(module)
    def call_singleton(x: int) -> tuple[bool]:
        return (foo,)(x)

    validate(module.compile())


def test_call(validate):
    module = GuppyModule("module")

    @guppy(module)
    def foo() -> int:
        return 42

    @guppy(module)
    def bar() -> bool:
        return True

    @guppy(module)
    def baz() -> tuple[int, bool]:
        return (foo, bar)()

    validate(module.compile())


def test_call_inplace(validate):
    module = GuppyModule("module")

    @guppy(module)
    def local(f: Callable[[int], bool], g: Callable[[bool], int]) -> tuple[bool, int]:
        return (f, g)(42, True)

    validate(module.compile())


def test_call_back(validate):
    module = GuppyModule("module")

    @guppy(module)
    def foo(x: int) -> int:
        return x

    @guppy(module)
    def bar(x: int) -> int:
        return x * x

    @guppy(module)
    def baz(x: int, y: int) -> tuple[int, int]:
        return (foo, bar)(x, y)

    validate(module.compile())


def test_normal(validate):
    module = GuppyModule("module")

    @guppy(module)
    def glo(x: int) -> int:
        return x

    @guppy(module)
    def foo(x: int) -> int:
        return glo(x)

    validate(module.compile())
