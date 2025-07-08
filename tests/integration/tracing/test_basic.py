from collections.abc import Callable

from guppylang.decorator import guppy
from guppylang.std.builtins import array, comptime

from hugr import ops
from hugr.std.int import IntVal


def test_flat(validate):
    @guppy.comptime
    def foo() -> int:
        x = 0
        for i in range(10):
            x += i
        return x

    hugr = guppy.compile(foo)
    assert hugr.module.num_nodes() == 6
    [const] = [
        data.op for _, data in hugr.module.nodes() if isinstance(data.op, ops.Const)
    ]
    assert isinstance(const.val, IntVal)
    assert const.val.v == sum(i for i in range(10))
    validate(hugr)


def test_inputs(validate):
    @guppy.comptime
    def foo(x: int, y: float) -> tuple[int, float]:
        return x, y

    validate(guppy.compile(foo))


def test_recursion(validate):
    @guppy.comptime
    def foo(x: int) -> int:
        # `foo` doesn't terminate but the compiler should!
        return foo(x)

    validate(guppy.compile(foo))


def test_calls(validate):
    @guppy.comptime
    def comptime1(x: int) -> int:
        return regular1(x)

    @guppy
    def regular1(x: int) -> int:
        return comptime2(x)

    @guppy.comptime
    def comptime2(x: int) -> int:
        return regular2(x)

    @guppy
    def regular2(x: int) -> int:
        return comptime1(x)

    validate(guppy.compile(regular2))


def test_load_func(validate):
    @guppy.declare
    def foo(x: int) -> int: ...

    @guppy.comptime
    def test() -> Callable[[int], int]:
        return foo

    validate(guppy.compile(test))


def test_inner_scope(validate):
    def make(n: int):
        # Test that `n` is scope even if it is only defined in this function scope
        # instead of globally:

        @guppy.comptime
        def foo() -> int:
            return n

        @guppy.comptime
        def bar(xs: array[int, comptime(n)]) -> None:
            pass

        return foo, bar

    foo, bar = make(42)
    validate(guppy.compile(foo))
    validate(guppy.compile(bar))
