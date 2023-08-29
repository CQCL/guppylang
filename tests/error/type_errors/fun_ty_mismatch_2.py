from typing import Callable

from tests.error.util import guppy


@guppy
def foo(x: int) -> int:
    def bar(f: Callable[[], int]) -> int:
        return f()

    return bar(foo)
