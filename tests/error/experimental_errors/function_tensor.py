from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")


@guppy(module)
def f(x: int) -> int:
    return x


@guppy(module)
def g(x: int) -> int:
    return x


@guppy(module)
def main() -> tuple[int, int]:
    return (f, g)(1, 2)


module.compile()
