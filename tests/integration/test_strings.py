from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from tests.util import compile_guppy

import pytest

def test_basic_type(validate):
    @compile_guppy
    def foo(x: str) -> str:
        return x

    validate(foo)


@pytest.mark.skip("Unsupported, see https://github.com/CQCL/hugr/issues/1817")
def test_basic_value(validate):
    @compile_guppy
    def foo() -> str:
        x = "Hello World"
        return x

    validate(foo)


@pytest.mark.skip("Unsupported, see https://github.com/CQCL/hugr/issues/1817")
def test_struct(validate):
    module = GuppyModule("module")

    @guppy.struct(module)
    class StringStruct:
        x: str

    @guppy(module)
    def main(s: StringStruct) -> None:
        StringStruct("Lorem Ipsum")

    validate(module.compile())