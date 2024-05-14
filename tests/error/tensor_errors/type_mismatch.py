from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")

@guppy.declare(module)
def foo(x: int) -> int:
    ...

@guppy(module)
def main() -> int:
    return (foo, foo)(42, False)

module.compile()
