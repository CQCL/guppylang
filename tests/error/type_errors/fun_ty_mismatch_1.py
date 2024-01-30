from collections.abc import Callable

from tests.util import compile_guppy


@compile_guppy
def foo() -> Callable[[int], int]:
    def bar(x: int) -> bool:
        return x > 0

    return bar
