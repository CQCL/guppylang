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
    def bar() -> Callable[[int], tuple[bool]]:
        return (foo,)

    @guppy(module)
    def baz(x: int) -> tuple[bool]:
        return (foo,)(x)

    @guppy(module)
    def baz2(x: int) -> tuple[bool]:
        return bar()(x)

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
    def baz_ho() -> Callable[[], tuple[int, bool]]:
        return (foo, bar)

    @guppy(module)
    def baz_ho_call() -> tuple[int, bool]:
        return baz_ho()()

    @guppy(module)
    def baz() -> tuple[int, bool]:
        return (foo, bar)()

    @guppy(module)
    def local_ho(
        f: Callable[[int], bool], g: Callable[[bool], int]
    ) -> Callable[[int, bool], tuple[bool, int]]:
        return (f, g)

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


def test_higher_order(validate):
    module = GuppyModule("module")

    @guppy(module)
    def foo(x: int) -> bool:
        return x > 42

    @guppy(module)
    def bar(x: float) -> int:
        if x < 5.0:
            return 0
        else:
            return 1

    @guppy(module)
    def baz() -> Callable[[int, float], tuple[bool, int]]:
        return foo, bar

    # For the future:
    #
    #     @guppy(module)
    #     def apply(f: Callable[[int, float],
    #               tuple[bool, int]],
    #               args: tuple[int, float]) -> tuple[bool, int]:
    #         return f(*args)
    #
    #     @guppy(module)
    #     def apply_call(args: tuple[int, float]) -> tuple[bool, int]:
    #         return apply(baz, args)

    validate(module.compile())


# Check that we can parse and check against the `tensor` type
def tensor_type(validate):
    module = GuppyModule("module")

    @guppy(module)
    def foo(x: int) -> bool: ...

    @guppy(module)
    def bar(y: float, z: bool) -> int: ...

    @guppy(module)
    def baz() -> tensor[[int, float, bool], [bool, int]]:
        return foo, bar

    @guppy(module)
    def bazr(t: tensor[[int, float, bool], [bool, int]]) -> tuple[bool, int]:
        x, y = t(0, 1.0, True)
        return x, y

    @guppy(module)
    def main() -> tuple[bool, int]:
        return bazr(baz())

    validate(module.compile())
