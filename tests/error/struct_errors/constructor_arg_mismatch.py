from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("test")


@guppy.struct(module)
class MyStruct:
    x: tuple[int, int]


@guppy(module)
def main() -> None:
    MyStruct(0)


module.compile()
