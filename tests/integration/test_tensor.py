# ruff: noqa: F821
# ^ Stop ruff complaining about not knowing what "tensor" is

from collections.abc import Callable

from guppylang.decorator import guppy
from guppylang.module import GuppyModule


def test_check_callable(validate):
    module = GuppyModule("module")

    @guppy(module)
    def bar(f: Callable[[int], bool]) -> Callable[[int], bool]:
        return f

    @guppy(module)
    def foo(f: Callable[[int], bool]) -> tuple[Callable[[int], bool]]:
        return (f,)

    @guppy(module)
    def is_42(x: int) -> bool:
        return x == 42

    @guppy(module)
    def baz(x: int) -> bool:
        return foo(is_42)(x)

    @guppy(module)
    def baz1() -> tuple[Callable[[int], bool]]:
        return foo(is_42)

    @guppy(module)
    def baz2(x: int) -> bool:
        return (foo,)(is_42)(x)

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
    def baz_ho() -> tuple[Callable[[], int], Callable[[], bool]]:
        return (foo, bar)

    @guppy(module)
    def baz_ho_id() -> tuple[Callable[[], int], Callable[[], bool]]:
        return baz_ho()

    @guppy(module)
    def baz_ho_call() -> tuple[int, bool]:
        return baz_ho_id()()

    @guppy(module)
    def baz() -> tuple[int, bool]:
        return (foo, bar)()

    @guppy(module)
    def call_var() -> tuple[int, bool, int]:
        f = foo
        g = (foo, bar, f)
        return g()

    validate(module.compile())


def test_call_inplace(validate):
    module = GuppyModule("module")

    @guppy(module)
    def local(f: Callable[[int], bool], g: Callable[[bool], int]) -> tuple[bool, int]:
        return (f, g)(42, True)

    validate(module.compile())


def test_singleton(validate):
    module = GuppyModule("module")

    @guppy(module)
    def foo(x: int, y: int) -> tuple[int, int]:
        return y, x

    @guppy(module)
    def baz(x: int) -> tuple[int, int]:
        return (foo,)(x, x)

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

    @guppy(module)
    def call_var(x: int) -> tuple[int, int, int]:
        f = foo, baz
        return f(x, x, x)

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
    def baz() -> tuple[Callable[[int], bool], Callable[[float], int]]:
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


def test_nesting(validate):
    module = GuppyModule("module")

    @guppy(module)
    def foo(x: int, y: int) -> int:
        return x + y

    @guppy(module)
    def bar(x: int) -> int:
        return -x

    @guppy(module)
    def call(x: int) -> tuple[int, int, int]:
        f = bar, (bar, foo)
        return f(x, x, x, x)

    validate(module.compile())
