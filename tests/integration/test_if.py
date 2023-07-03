import pytest

from guppy.compiler import guppy
from tests.integration.util import validate


def test_if_no_else():
    @guppy
    def foo(x: bool, y: int) -> int:
        if x:
            y += 1
        return y

    validate(foo)


def test_if_else():
    @guppy
    def foo(x: bool, y: int) -> int:
        if x:
            y += 1
        else:
            y -= 1
        return y

    validate(foo)


def test_if_elif():
    @guppy
    def foo(x: bool, y: int) -> int:
        if x:
            y += 1
        elif y > 4:
            y *= 7
        return y

    validate(foo)


def test_if_elif_else():
    @guppy
    def foo(x: bool, y: int) -> int:
        if x:
            y += 1
        elif y > 4:
            y *= 7
        else:
            y = 1337
        return y

    validate(foo)


def test_if_return():
    @guppy
    def foo(x: bool, y: int) -> int:
        if x:
            return y
        y *= 32
        return y

    validate(foo)


def test_else_return():
    @guppy
    def foo(x: bool, y: int) -> int:
        if x:
            y += 3
        else:
            y /= 4
            return y
        return y

    validate(foo)


def test_both_return():
    @guppy
    def foo(x: bool, y: int) -> int:
        if x:
            y += 3
            return y
        else:
            y /= 4
            return y

    validate(foo)


def test_nested_return():
    @guppy
    def foo(x: int, y: int) -> int:
        if x > 5:
            if y == 4:
                x *= 4
            else:
                return y
        return x

    validate(foo)


def test_return_defined1():
    @guppy
    def foo(x: int, y: int) -> int:
        if x > 5:
            return y
        else:
            z = 5
        return z

    validate(foo)


def test_return_defined2():
    @guppy
    def foo(x: int) -> int:
        if x > 5:
            z = 45
        else:
            return x
        return z

    validate(foo)


def test_break_different_types1():
    @guppy
    def foo(x: int) -> int:
        z = 0
        while True:
            if x > 5:
                z = False
                break
            else:
                z = 8
            z += x
        return 0

    validate(foo)


def test_break_different_types2():
    @guppy
    def foo(x: int) -> int:
        z = 0
        while True:
            if x > 5:
                z = 8
            else:
                z = True
                break
            z += x
        return 0

    validate(foo)


@pytest.mark.skip("Known bug")
def test_continue_different_types1():
    @guppy
    def foo(x: int) -> int:
        z = 0
        while True:
            if x > 5:
                z = False
                continue
            else:
                z = 8
            z += x
        return z

    validate(foo)


@pytest.mark.skip("Known bug")
def test_continue_different_types2():
    @guppy
    def foo(x: int) -> int:
        z = 0
        while True:
            if x > 5:
                z = 8
            else:
                z = False
                continue
            z += x
        return z

    validate(foo)

