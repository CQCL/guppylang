"""Tests for using python expressions in guppy functions."""

from importlib.util import find_spec


from guppylang.decorator import guppy
from guppylang.std.builtins import py, comptime, array, frozenarray, nat, owned
from tests.util import compile_guppy

tket_installed = find_spec("tket") is not None


def test_basic(validate):
    x = 42

    @guppy
    def foo() -> int:
        return comptime(x + 1)

    validate(guppy.compile(foo))


def test_py_alias(validate):
    x = 42

    @guppy
    def foo() -> int:
        return py(x + 1)

    validate(guppy.compile(foo))


def test_builtin(validate):
    @compile_guppy
    def foo() -> int:
        return comptime(len({"a": 1337, "b": None}))

    validate(foo)


def test_if(validate):
    b = True

    @guppy
    def foo() -> int:
        if comptime(b or 1 > 6):
            return 0
        return 1

    validate(guppy.compile(foo))


def test_redeclare_after(validate):
    x = 1

    @guppy
    def foo() -> bool:
        return comptime(x)

    x = False

    validate(guppy.compile(foo))


def test_tuple(validate):
    @compile_guppy
    def foo() -> int:
        x, y = comptime((1, False))
        return x

    validate(foo)


def test_tuple_implicit(validate):
    @compile_guppy
    def foo() -> int:
        x, y = comptime(1, False)
        return x

    validate(foo)


def test_list_basic(validate):
    @compile_guppy
    def foo() -> frozenarray[int, 3]:
        xs = comptime([1, 2, 3])
        return xs

    validate(foo)


def test_list_empty(validate):
    @compile_guppy
    def foo() -> frozenarray[int, 0]:
        return comptime([])

    validate(foo)


def test_list_empty_nested(validate):
    @compile_guppy
    def foo() -> None:
        xs: frozenarray[tuple[int, frozenarray[bool, 0]], 1] = comptime([(42, [])])

    validate(foo)


def test_list_empty_multiple(validate):
    @compile_guppy
    def foo() -> None:
        xs: tuple[frozenarray[int, 0], frozenarray[bool, 0]] = comptime([], [])

    validate(foo)


def test_nats_from_ints(validate):
    @compile_guppy
    def foo() -> None:
        x: nat = comptime(1)
        y: tuple[nat, nat] = comptime(2, 3)
        z: frozenarray[nat, 3] = comptime([4, 5, 6])

    validate(foo)


def test_strings(validate):
    @compile_guppy
    def foo() -> None:
        x: str = comptime("a" + "b")

    validate(foo)


def test_func_type_arg(validate):
    n = 10

    @guppy
    def foo(xs: array[int, comptime(n)] @ owned) -> array[int, comptime(n)]:
        return xs

    @guppy.declare
    def bar(xs: array[int, comptime(n)]) -> array[int, comptime(n)]: ...

    @guppy.struct
    class Baz:
        xs: array[int, comptime(n)]

    validate(guppy.compile(foo))
    validate(guppy.compile(bar))
    validate(guppy.compile(Baz))
