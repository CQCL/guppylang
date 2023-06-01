from guppy.compiler import guppy, GuppyModule
from tests.integration.util import validate


def test_call(tmp_path):
    module = GuppyModule("module")

    @module
    def foo() -> int:
        return 42

    @module
    def bar() -> int:
        return bar()

    validate(module.compile(exit_on_error=True), tmp_path)


def test_call_back(tmp_path):
    module = GuppyModule("module")

    @module
    def foo(x: int) -> int:
        return bar(x)

    @module
    def bar(x: int) -> int:
        return x

    validate(module.compile(exit_on_error=True), tmp_path)


def test_recursion(tmp_path):
    @guppy
    def main(x: int) -> int:
        return main(x)

    validate(main, tmp_path)


def test_mutual_recursion(tmp_path):
    module = GuppyModule("module")

    @module
    def foo(x: int) -> int:
        return bar(x)

    @module
    def bar(x: int) -> int:
        return foo(x)

    validate(module.compile(exit_on_error=True), tmp_path)



