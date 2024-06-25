from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("test")


@guppy.struct(module)
class MyStruct:
    x: int


@guppy(module)
def main() -> None:
    MyStruct(1, 2, 3)


module.compile()
