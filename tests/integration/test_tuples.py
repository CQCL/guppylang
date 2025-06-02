from tests.util import compile_guppy

import pytest

@pytest.mark.skip()
def test_index1(validate):
    @compile_guppy
    def foo(t: tuple[int, int]) -> int:
        return t[0]

    validate(foo)

def test_index2(validate):
    @compile_guppy
    def foo() -> int:
        t = (1, 2, 3)
        x = t[1]
        return x

    validate(foo)

@pytest.mark.skip()
def test_index3(validate):
    @compile_guppy
    def foo() -> int:
        return (1, 2, 3)[2]

    validate(foo)

@pytest.mark.skip()
def test_index_dynamic(validate):
    @compile_guppy
    def foo(x: int) -> int:
        return (1, 2, 3)[x]

    validate(foo)

from guppylang.std.builtins import array
from guppylang.decorator import guppy
from guppylang.module import GuppyModule

@pytest.mark.skip()
def test_array(validate):
    @compile_guppy
    def foo() -> int:
        xs = array(1, 2, 3)
        i = 2
        x = xs[2]
        return x

    validate(foo)

@pytest.mark.skip()
def test_comptime(validate):
    module = GuppyModule("module")

    @guppy.comptime(module)
    def bar(t: tuple[int, int]) -> int:
        return t[0]

    @guppy(module)
    def foo() -> int:
        t = (2, 2)
        return bar(t)

    validate(module.compile())