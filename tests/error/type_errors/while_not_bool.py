import tests.error.util
from guppy.decorator import guppy
from guppy.module import GuppyModule
from tests.error.util import NonBool

module = GuppyModule("test")
module.load(tests.error.util)


@guppy(module)
def foo(x: NonBool) -> int:
    while x:
        pass
    return 0


module.compile()
