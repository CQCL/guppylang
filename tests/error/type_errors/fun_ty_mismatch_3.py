from collections.abc import Callable

from guppy.decorator import guppy


@guppy
def foo(x: int) -> int:
    def bar(f: Callable[[int], bool]) -> bool:
        return f(42)

    return bar(foo)
