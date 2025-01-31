"""Tests for using python expressions in guppy functions."""

from importlib.util import find_spec


from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import py, array, nat, owned
from tests.util import compile_guppy

tket2_installed = find_spec("tket2") is not None


def test_basic(validate):
    x = 42

    @compile_guppy
    def foo() -> int:
        return py(x + 1)

    validate(foo)


def test_builtin(validate):
    @compile_guppy
    def foo() -> int:
        return py(len({"a": 1337, "b": None}))

    validate(foo)


def test_if(validate):
    b = True

    @compile_guppy
    def foo() -> int:
        if py(b or 1 > 6):
            return 0
        return 1

    validate(foo)


def test_redeclare_after(validate):
    x = 1

    @compile_guppy
    def foo() -> int:
        return py(x)

    x = False

    validate(foo)


def test_tuple(validate):
    @compile_guppy
    def foo() -> int:
        x, y = py((1, False))
        return x

    validate(foo)


def test_tuple_implicit(validate):
    @compile_guppy
    def foo() -> int:
        x, y = py(1, False)
        return x

    validate(foo)


def test_list_basic(validate):
    @compile_guppy
    def foo() -> array[int, 3]:
        xs = py([1, 2, 3])
        return xs

    validate(foo)


def test_list_empty(validate):
    @compile_guppy
    def foo() -> array[int, 0]:
        return py([])

    validate(foo)


def test_list_empty_nested(validate):
    @compile_guppy
    def foo() -> None:
        xs: array[tuple[int, array[bool, 0]], 1] = py([(42, [])])

    validate(foo)


def test_list_empty_multiple(validate):
    @compile_guppy
    def foo() -> None:
        xs: tuple[array[int, 0], array[bool, 0]] = py([], [])

    validate(foo)


def test_nats_from_ints(validate):
    @compile_guppy
    def foo() -> None:
        x: nat = py(1)
        y: tuple[nat, nat] = py(2, 3)
        z: array[nat, 3] = py([4, 5, 6])

    validate(foo)


def test_strings(validate):
    @compile_guppy
    def foo() -> None:
        x: str = py("a" + "b")

    validate(foo)


def test_func_type_arg(validate):
    module = GuppyModule("test")
    n = 10

    @guppy(module)
    def foo(xs: array[int, py(n)] @ owned) -> array[int, py(n)]:
        return xs

    @guppy.declare(module)
    def bar(xs: array[int, py(n)]) -> array[int, py(n)]: ...

    @guppy.struct(module)
    class Baz:
        xs: array[int, py(n)]

    validate(module.compile())
