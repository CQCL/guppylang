import pytest

from guppylang.decorator import guppy
from guppylang.module import GuppyModule


def test_func_redefinition(validate):
    module = GuppyModule("test")

    @guppy(module)
    def test() -> bool:
        return 5  # Type error on purpose

    @guppy(module)
    def test() -> bool:  # noqa: F811
        return False

    validate(module.compile())


def test_method_redefinition(validate):
    module = GuppyModule("test")

    @guppy.struct(module)
    class Test:
        x: int

        @guppy(module)
        def foo(self: "Test") -> int:
            return 1.0  # Type error on purpose

        @guppy(module)
        def foo(self: "Test") -> int:
            return 1  # Type error on purpose

    validate(module.compile())


def test_redefine_after_error(validate):
    module = GuppyModule("test")

    @guppy.struct(module)
    class Foo:
        x: int

    @guppy(module)
    def foo() -> int:
        return y

    try:
        module.compile()
    except:
        pass

    @guppy.struct(module)
    class Foo:
        x: int

    @guppy(module)
    def foo(f: Foo) -> int:
        return f.x

    validate(module.compile())


@pytest.mark.skip("See https://github.com/CQCL/guppylang/issues/456")
def test_struct_redefinition(validate):
    module = GuppyModule("test")

    @guppy.struct(module)
    class Test:
        x: "blah"  # Non-existing type

    @guppy.struct(module)
    class Test:
        y: int

    @guppy(module)
    def main(x: int) -> Test:
        return Test(x)

    validate(module.compile())


@pytest.mark.skip("See https://github.com/CQCL/guppylang/issues/456")
def test_struct_method_redefinition(validate):
    module = GuppyModule("test")

    @guppy.struct(module)
    class Test:
        x: int

        @guppy(module)
        def foo(self: "Test") -> int:
            return 1.0  # Type error on purpose

    @guppy.struct(module)
    class Test:
        y: int

        @guppy(module)
        def bar(self: "Test") -> int:
            return self.y

    @guppy(module)
    def main(x: int) -> int:
        return Test(x).bar()

    validate(module.compile())

