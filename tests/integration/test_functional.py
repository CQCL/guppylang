import pytest

from guppylang.decorator import guppy
from tests.integration.util import functional, _


@pytest.mark.skip()
def test_if_no_else(validate):
    @guppy
    def foo(x: bool, y: int) -> int:
        _ @ functional
        if x:
            y += 1
        return y

    validate(foo)


@pytest.mark.skip()
def test_if_else(validate):
    @guppy
    def foo(x: bool, y: int) -> int:
        _ @ functional
        if x:
            y += 1
        else:
            y -= 1
        return y

    validate(foo)


@pytest.mark.skip()
def test_if_elif(validate):
    @guppy
    def foo(x: bool, y: int) -> int:
        _ @ functional
        if x:
            y += 1
        elif y > 4:
            y *= 7
        return y

    validate(foo)


@pytest.mark.skip()
def test_if_elif_else(validate):
    @guppy
    def foo(x: bool, y: int) -> int:
        _ @ functional
        if x:
            y += 1
        elif y > 4:
            y *= 7
        else:
            y = 1337
        return y

    validate(foo)


@pytest.mark.skip()
def test_infinite_loop(validate):
    @guppy
    def foo() -> int:
        while True:
            pass
        return 0

    validate(foo)


@pytest.mark.skip()
def test_counting_loop(validate):
    @guppy
    def foo(i: int) -> int:
        while i > 0:
            i -= 1
        return 0

    validate(foo)


@pytest.mark.skip()
def test_nested_loop(validate):
    @guppy
    def foo(x: int, y: int) -> int:
        p = 0
        _ @ functional
        while x > 0:
            s = 0
            while y > 0:
                s += x
                y -= 1
            p += s
            x -= 1
        return p

    validate(foo)
