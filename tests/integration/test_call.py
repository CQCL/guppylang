from guppy.compiler import guppy, GuppyModule
from tests.integration.util import validate


def test_call():
    module = GuppyModule("module")

    @module
    def foo() -> int:
        return 42

    @module
    def bar() -> int:
        return foo()

    validate(module.compile(exit_on_error=True))


def test_call_back(tmp_path):
    module = GuppyModule("module")

    @module
    def foo(x: int) -> int:
        return bar(x)

    @module
    def bar(x: int) -> int:
        return x

    validate(module.compile(exit_on_error=True))


def test_recursion():
    @guppy
    def main(x: int) -> int:
        return main(x)

    validate(main)


def test_mutual_recursion():
    module = GuppyModule("module")

    @module
    def foo(x: int) -> int:
        return bar(x)

    @module
    def bar(x: int) -> int:
        return foo(x)

    validate(module.compile(exit_on_error=True))



