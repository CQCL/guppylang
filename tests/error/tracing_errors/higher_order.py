from collections.abc import Callable

from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")


@guppy.comptime(module)
def test(f: Callable[[], int]) -> int:
    return f()


module.compile()
