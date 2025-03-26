from collections.abc import Callable

from guppylang.decorator import guppy
from guppylang.module import GuppyModule

from hugr import ops
from hugr.std.int import IntVal


def test_flat(validate):
    module = GuppyModule("module")

    @guppy.comptime(module)
    def foo() -> int:
        x = 0
        for i in range(10):
            x += i
        return x

    hugr = module.compile()
    assert hugr.module.num_nodes() == 6
    [const] = [
        data.op for _, data in hugr.module.nodes() if isinstance(data.op, ops.Const)
    ]
    assert isinstance(const.val, IntVal)
    assert const.val.v == sum(i for i in range(10))
    validate(hugr)


def test_inputs(validate):
    module = GuppyModule("module")

    @guppy.comptime(module)
    def foo(x: int, y: float) -> tuple[int, float]:
        return x, y

    validate(module.compile())


def test_recursion(validate):
    module = GuppyModule("module")

    @guppy.comptime(module)
    def foo(x: int) -> int:
        # `foo` doesn't terminate but the compiler should!
        return foo(x)

    validate(module.compile())


def test_calls(validate):
    module = GuppyModule("module")

    @guppy.comptime(module)
    def comptime1(x: int) -> int:
        return regular1(x)

    @guppy(module)
    def regular1(x: int) -> int:
        return comptime2(x)

    @guppy.comptime(module)
    def comptime2(x: int) -> int:
        return regular2(x)

    @guppy(module)
    def regular2(x: int) -> int:
        return comptime1(x)

    validate(module.compile())


def test_load_func(validate):
    module = GuppyModule("test")

    @guppy.declare(module)
    def foo(x: int) -> int: ...

    @guppy.comptime(module)
    def test() -> Callable[[int], int]:
        return foo

    validate(module.compile())

