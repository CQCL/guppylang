from guppylang.decorator import guppy
from guppylang.module import GuppyModule


def test_call(validate):
    module = GuppyModule("module")

    @guppy(module)
    def foo() -> int:
        return 42

    @guppy(module)
    def bar() -> int:
        return foo()

    validate(module.compile())


def test_call_back(validate):
    module = GuppyModule("module")

    @guppy(module)
    def foo(x: int) -> int:
        return bar(x)

    @guppy(module)
    def bar(x: int) -> int:
        return x

    validate(module.compile())


def test_recursion(validate):
    @guppy(compile=True)
    def main(x: int) -> int:
        return main(x)

    validate(main)


def test_mutual_recursion(validate):
    module = GuppyModule("module")

    @guppy(module)
    def foo(x: int) -> int:
        return bar(x)

    @guppy(module)
    def bar(x: int) -> int:
        return foo(x)

    validate(module.compile())
