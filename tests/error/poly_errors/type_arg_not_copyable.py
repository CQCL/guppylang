from guppylang import array
from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")

T = guppy.type_var("T", copyable=True, droppable=False, module=module)


@guppy(module)
def foo(x: T) -> T:
    return x


@guppy(module)
def main() -> None:
    f = foo[array[int, 10]]


module.compile()
