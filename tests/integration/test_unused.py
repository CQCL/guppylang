"""All sorts of weird stuff is allowed when variables are not used."""

from tests.util import compile_guppy


def test_not_always_defined1(validate):
    @compile_guppy
    def foo(x: bool) -> int:
        if x:
            z = 5
        return 4

    validate(foo)


def test_not_always_defined2(validate):
    @compile_guppy
    def foo(x: bool) -> int:
        if x:
            pass
        else:
            z = 5
        return 4

    validate(foo)


def test_not_always_defined3(validate):
    @compile_guppy
    def foo(x: bool) -> int:
        if x:
            y = True
        else:
            z = 5
        return 4

    validate(foo)


def test_different_types1(validate):
    @compile_guppy
    def foo(x: bool) -> int:
        if x:
            z = True
        else:
            z = 5
        return 4

    validate(foo)


def test_different_types2(validate):
    @compile_guppy
    def foo(x: bool) -> int:
        z = False
        if x:
            z = True
        else:
            z = 5
        return 4

    validate(foo)


def test_different_types3(validate):
    @compile_guppy
    def foo(x: bool) -> int:
        z = False
        if x:
            z = True
        else:
            z = 5
        return 4

    validate(foo)


def test_while_change_type(validate):
    @compile_guppy
    def foo() -> None:
        x = 42
        while True:
            x = True

    validate(foo)


def test_if_expr_different_types(validate):
    @compile_guppy
    def foo(x: bool) -> None:
        5 if x else False

    validate(foo)
