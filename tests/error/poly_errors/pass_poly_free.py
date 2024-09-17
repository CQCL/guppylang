from typing import Callable

from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("test")

T = guppy.type_var("T", module=module)


@guppy.declare(module)
def foo(f: Callable[[T], T]) -> None:
    ...


@guppy.declare(module)
def bar(x: T) -> T:
    ...


@guppy(module)
def main() -> None:
    foo(bar)


module.compile()
