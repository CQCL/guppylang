import tests.error.util
from guppy.decorator import guppy
from guppy.module import GuppyModule
from tests.error.util import NonBool

module = GuppyModule("test")
module.load(tests.error.util)


@guppy(module)
def foo(x: NonBool, y: bool) -> bool:
    return x and y


module.compile()
