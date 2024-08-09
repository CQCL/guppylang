from typing import Callable

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import inout


module = GuppyModule("test")


@guppy.declare(module)
def foo(f: Callable[[int @inout], None]) -> None: ...


module.compile()
