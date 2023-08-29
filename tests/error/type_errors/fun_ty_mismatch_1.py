from typing import Callable

from tests.error.util import guppy


@guppy
def foo() -> Callable[[int], int]:
    def bar(x: int) -> bool:
        return x > 0

    return bar
