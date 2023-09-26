import tests.error.util

from guppy.compiler import GuppyModule
from tests.error.util import NonBool

module = GuppyModule("test")
module.load(tests.error.util)


@module
def foo(x: NonBool) -> int:
    while x:
        pass
    return 0


module.compile(True)
