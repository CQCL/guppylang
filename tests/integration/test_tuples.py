from tests.util import compile_guppy
from guppylang.decorator import guppy

import pytest

def test_index1(validate):
    @compile_guppy
    def foo(t: tuple[int, float]) -> int:
        return t[0]

    validate(foo)

def test_index2(validate, run_int_fn):
    @guppy
    def main() -> int:
        t = (1, 2, 2.2)
        x = t[1]
        return x

    compiled = guppy.compile(main)
    validate(compiled)
    run_int_fn(compiled, 2)

def test_index3(validate):
    @compile_guppy
    def foo() -> int:
        return (1, 2, 3)[2]

    validate(foo)

def test_index_dynamic(validate):
    @compile_guppy
    def foo(x: int) -> int:
        return (1, 2, 3)[x]

    validate(foo)


def test_comptime(validate):
    @guppy.comptime
    def bar(t: tuple[int, int]) -> int:
        return t[0]

    @guppy
    def foo() -> int:
        t = (2, 2)
        return bar(t)

    validate(guppy.compile(foo))