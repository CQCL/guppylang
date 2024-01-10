from typing import Callable

from guppy.decorator import guppy
from guppy.module import GuppyModule


module = GuppyModule("test")

T = guppy.type_var(module, "T")


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
