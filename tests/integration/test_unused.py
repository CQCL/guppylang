import pytest

from guppy.compiler import guppy
from tests.integration.util import validate

""" All sorts of weird stuff is allowed when variables are not used. """


def test_not_always_defined1(tmp_path):
    @guppy
    def foo(x: bool) -> int:
        if x:
            z = 5
        return 4

    validate(foo, tmp_path)


def test_not_always_defined2(tmp_path):
    @guppy
    def foo(x: bool) -> int:
        if x:
            pass
        else:
            z = 5
        return 4

    validate(foo, tmp_path)


def test_not_always_defined3(tmp_path):
    @guppy
    def foo(x: bool) -> int:
        if x:
            y = True
        else:
            z = 5
        return 4

    validate(foo, tmp_path)


def test_different_types1(tmp_path):
    @guppy
    def foo(x: bool) -> int:
        if x:
            z = True
        else:
            z = 5
        return 4

    validate(foo, tmp_path)


def test_different_types2(tmp_path):
    @guppy
    def foo(x: bool) -> int:
        z = False
        if x:
            z = True
        else:
            z = 5
        return 4

    validate(foo, tmp_path)


def test_different_types3(tmp_path):
    @guppy
    def foo(x: bool) -> int:
        z = False
        if x:
            z = True
        else:
            z = 5
        return 4

    validate(foo, tmp_path)


@pytest.mark.skip("Known bug")
def test_while_change_type(tmp_path):
    @guppy
    def foo() -> None:
        x = 42
        while True:
            x = True

    validate(foo, tmp_path)
