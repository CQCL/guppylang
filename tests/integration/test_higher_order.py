from collections.abc import Callable

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from tests.util import compile_guppy


def test_basic(validate):
    module = GuppyModule("test")

    @guppy(module)
    def bar(x: int) -> bool:
        return x > 0

    @guppy(module)
    def foo() -> Callable[[int], bool]:
        return bar

    validate(module.compile())


def test_call_1(validate):
    module = GuppyModule("test")

    @guppy(module)
    def bar() -> bool:
        return False

    @guppy(module)
    def foo() -> Callable[[], bool]:
        return bar

    @guppy(module)
    def baz() -> bool:
        return foo()()

    validate(module.compile())


def test_call_2(validate):
    module = GuppyModule("test")

    @guppy(module)
    def bar(x: int) -> Callable[[int], None]:
        return bar(x - 1)

    @guppy(module)
    def foo() -> Callable[[int], Callable[[int], None]]:
        return bar

    @guppy(module)
    def baz(y: int) -> None:
        return foo()(y)(y)

    validate(module.compile())


def test_method(validate):
    module = GuppyModule("module")

    @guppy(module)
    def foo(x: int) -> tuple[int, Callable[[int], int]]:
        f = x.__add__
        return f(1), f

    validate(module.compile())


def test_nested(validate):
    @compile_guppy
    def foo(x: int) -> Callable[[int], bool]:
        def bar(y: int) -> bool:
            return x > y

        return bar

    validate(foo)


def test_nested_capture_struct(validate):
    module = GuppyModule("test")

    @guppy.struct(module)
    class MyStruct:
        x: int

    @guppy(module)
    def foo(s: MyStruct) -> Callable[[int], bool]:
        def bar(y: int) -> bool:
            return s.x > y

        return bar

    validate(module.compile())


def test_curry(validate):
    module = GuppyModule("curry")

    @guppy(module)
    def curry(f: Callable[[int, int], bool]) -> Callable[[int], Callable[[int], bool]]:
        def g(x: int) -> Callable[[int], bool]:
            def h(y: int) -> bool:
                return f(x, y)

            return h

        return g

    @guppy(module)
    def uncurry(
        f: Callable[[int], Callable[[int], bool]],
    ) -> Callable[[int, int], bool]:
        def g(x: int, y: int) -> bool:
            return f(x)(y)

        return g

    @guppy(module)
    def gt(x: int, y: int) -> bool:
        return x > y

    @guppy(module)
    def main(x: int, y: int) -> None:
        curried = curry(gt)
        curried(x)(y)
        uncurried = uncurry(curried)
        uncurried(x, y)
        curry(uncurry(curry(gt)))(y)(x)

    validate(module.compile())


def test_y_combinator(validate):
    module = GuppyModule("fib")

    @guppy(module)
    def fac_(f: Callable[[int], int], n: int) -> int:
        if n == 0:
            return 1
        return n * f(n - 1)

    @guppy(module)
    def Y(f: Callable[[Callable[[int], int], int], int]) -> Callable[[int], int]:
        def y(x: int) -> int:
            return f(Y(f), x)

        return y

    @guppy(module)
    def fac(x: int) -> int:
        return Y(fac_)(x)

    validate(module.compile())
