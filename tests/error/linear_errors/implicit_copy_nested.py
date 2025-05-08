from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array, owned

module = GuppyModule("test")


@guppy.struct(module)
class MyStruct:
    x: array[int, 1]


@guppy.declare(module)
def use(arr: array[int, 1] @owned) -> None: ...


@guppy(module)
def test(s: MyStruct) -> None:
    p = s.x
    use(s.x)


module.compile()