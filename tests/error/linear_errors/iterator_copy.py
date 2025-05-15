from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array, owned

module = GuppyModule("test")


@guppy.declare(module)
def use(q: array[int, 3] @owned) -> None: ...


@guppy(module)
def test(q: array[int, 3] @owned) -> None:
    for i in q:
        i + i
    use(q)

module.compile()
