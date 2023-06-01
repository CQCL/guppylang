from guppy.compiler import guppy
from tests.integration.util import validate


def test_if_no_else(tmp_path):
    @guppy
    def foo(x: bool, y: int) -> int:
        if x:
            y += 1
        return y

    validate(foo, tmp_path)


def test_if_else(tmp_path):
    @guppy
    def foo(x: bool, y: int) -> int:
        if x:
            y += 1
        else:
            y -= 1
        return y

    validate(foo, tmp_path)


def test_if_elif(tmp_path):
    @guppy
    def foo(x: bool, y: int) -> int:
        if x:
            y += 1
        elif y > 4:
            y *= 7
        return y

    validate(foo, tmp_path)


def test_if_elif_else(tmp_path):
    @guppy
    def foo(x: bool, y: int) -> int:
        if x:
            y += 1
        elif y > 4:
            y *= 7
        else:
            y = 1337
        return y

    validate(foo, tmp_path)


def test_if_return(tmp_path):
    @guppy
    def foo(x: bool, y: int) -> int:
        if x:
            return y
        y *= 32
        return y

    validate(foo, tmp_path)


def test_else_return(tmp_path):
    @guppy
    def foo(x: bool, y: int) -> int:
        if x:
            y += 3
        else:
            y /= 4
            return y
        return y

    validate(foo, tmp_path)


def test_both_return(tmp_path):
    @guppy
    def foo(x: bool, y: int) -> int:
        if x:
            y += 3
            return y
        else:
            y /= 4
            return y

    validate(foo, tmp_path)


