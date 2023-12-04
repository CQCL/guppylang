from collections.abc import Callable

from tests.error.util import guppy


@guppy
def foo(x: int) -> int:
    def bar(f: Callable[[int], bool]) -> bool:
        return f(42)

    return bar(foo)
