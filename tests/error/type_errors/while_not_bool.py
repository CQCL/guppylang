import tests.error.util

from guppy.compiler import GuppyModule, guppy
from tests.error.util import NonBool

module = GuppyModule("test")
module.load(tests.error.util)


@guppy(module)
def foo(x: NonBool) -> int:
    while x:
        pass
    return 0


module.compile(True)
