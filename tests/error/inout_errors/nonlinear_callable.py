from typing import Callable

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import owned


module = GuppyModule("test")


@guppy.declare(module)
def foo(f: Callable[[int @owned], None]) -> None: ...


module.compile()
