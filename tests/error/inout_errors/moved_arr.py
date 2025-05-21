from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array, owned

module = GuppyModule("test")


@guppy.declare(module)
def foo(q: array[int, 3]) -> None: ...


@guppy.declare(module)
def use(q: array[int, 3] @owned) -> None: ...


@guppy(module)
def test(q: array[int, 3]) -> None:
    foo(q)
    use(q)


module.compile()
