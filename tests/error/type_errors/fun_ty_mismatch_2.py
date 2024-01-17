from collections.abc import Callable

from guppylang.decorator import guppy


@guppy(compile=True)
def foo(x: int) -> int:
    def bar(f: Callable[[], int]) -> int:
        return f()

    return bar(foo)
