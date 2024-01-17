from guppylang.decorator import guppy
from tests.integration.util import py


def test_basic(validate):
    x = 42

    @guppy(compile=True)
    def foo() -> int:
        return py(x + 1)

    validate(foo)


def test_builtin(validate):
    @guppy(compile=True)
    def foo() -> int:
        return py(len({"a": 1337, "b": None}))

    validate(foo)


def test_if(validate):
    b = True

    @guppy(compile=True)
    def foo() -> int:
        if py(b or 1 > 6):
            return 0
        return 1

    validate(foo)


def test_redeclare_after(validate):
    x = 1

    @guppy(compile=True)
    def foo() -> int:
        return py(x)

    x = False

    validate(foo)


def test_tuple(validate):
    @guppy(compile=True)
    def foo() -> int:
        x, y = py((1, False))
        return x

    validate(foo)


def test_tuple_implicit(validate):
    @guppy(compile=True)
    def foo() -> int:
        x, y = py(1, False)
        return x

    validate(foo)
