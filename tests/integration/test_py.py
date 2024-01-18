from guppylang.decorator import guppy
from tests.integration.util import py


def test_basic(validate):
    x = 42

    @guppy
    def foo() -> int:
        return py(x + 1)

    validate(foo)


def test_builtin(validate):
    @guppy
    def foo() -> int:
        return py(len({"a": 1337, "b": None}))

    validate(foo)


def test_if(validate):
    b = True

    @guppy
    def foo() -> int:
        if py(b or 1 > 6):
            return 0
        return 1

    validate(foo)


def test_redeclare_after(validate):
    x = 1

    @guppy
    def foo() -> int:
        return py(x)

    x = False

    validate(foo)


def test_tuple(validate):
    @guppy
    def foo() -> int:
        x, y = py((1, False))
        return x

    validate(foo)


def test_tuple_implicit(validate):
    @guppy
    def foo() -> int:
        x, y = py(1, False)
        return x

    validate(foo)


def test_list_basic(validate):
    @guppy
    def foo() -> list[int]:
        xs = py([1, 2, 3])
        return xs

    validate(foo)


def test_list_empty(validate):
    @guppy
    def foo() -> list[int]:
        return py([])

    validate(foo)


def test_list_empty_nested(validate):
    @guppy
    def foo() -> None:
        xs: list[tuple[int, list[bool]]] = py([(42, [])])

    validate(foo)


def test_list_empty_multiple(validate):
    @guppy
    def foo() -> None:
        xs: tuple[list[int], list[bool]] = py([], [])

    validate(foo)
