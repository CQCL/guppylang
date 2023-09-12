from guppy.compiler import guppy, GuppyModule
from tests.integration.util import validate_module, validate


def test_call():
    module = GuppyModule("test_call")

    @module
    def foo() -> int:
        return 42

    @module
    def bar() -> int:
        return foo()

    validate_module(module, exit_on_error=True)


def test_call_back(tmp_path):
    module = GuppyModule("test_call_back")

    @module
    def foo(x: int) -> int:
        return bar(x)

    @module
    def bar(x: int) -> int:
        return x

    validate_module(module, exit_on_error=True)


def test_recursion():
    @guppy
    def main(x: int) -> int:
        return main(x)

    validate(main, "test_recursion")


def test_mutual_recursion():
    module = GuppyModule("test_mutual_recursion")

    @module
    def foo(x: int) -> int:
        return bar(x)

    @module
    def bar(x: int) -> int:
        return foo(x)

    validate_module(module, exit_on_error=True)
