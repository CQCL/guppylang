from typing import Callable, Optional, Any

from guppy.compiler import GuppyModule
from guppy.hugr.hugr import Hugr


def guppy(f: Callable[..., Any]) -> Optional[Hugr]:
    """ Decorator to compile functions outside of modules for testing. """
    module = GuppyModule("module")
    module(f)
    return module.compile(exit_on_error=True)
