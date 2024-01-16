from collections.abc import Callable

from guppy.decorator import guppy


@guppy
def foo(x: int) -> int:
    def bar(f: Callable[[], int]) -> int:
        return f()

    return bar(foo)
