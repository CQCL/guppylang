from collections.abc import Callable

from tests.util import compile_guppy


@compile_guppy
def foo(x: int) -> int:
    def bar(f: Callable[[], int]) -> int:
        return f()

    return bar(foo)
