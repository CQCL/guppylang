import pytest

from guppy.compiler import guppy
from tests.integration.util import validate

""" All sorts of weird stuff is allowed when variables are not used. """


def test_not_always_defined1():
    @guppy
    def foo(x: bool) -> int:
        if x:
            z = 5
        return 4

    validate(foo)


def test_not_always_defined2():
    @guppy
    def foo(x: bool) -> int:
        if x:
            pass
        else:
            z = 5
        return 4

    validate(foo)


def test_not_always_defined3():
    @guppy
    def foo(x: bool) -> int:
        if x:
            y = True
        else:
            z = 5
        return 4

    validate(foo)


def test_different_types1():
    @guppy
    def foo(x: bool) -> int:
        if x:
            z = True
        else:
            z = 5
        return 4

    validate(foo)


def test_different_types2():
    @guppy
    def foo(x: bool) -> int:
        z = False
        if x:
            z = True
        else:
            z = 5
        return 4

    validate(foo)


def test_different_types3():
    @guppy
    def foo(x: bool) -> int:
        z = False
        if x:
            z = True
        else:
            z = 5
        return 4

    validate(foo)


def test_while_change_type():
    @guppy
    def foo() -> None:
        x = 42
        while True:
            x = True

    validate(foo)
