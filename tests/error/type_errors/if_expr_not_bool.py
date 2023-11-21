import tests.error.util
from guppy.decorator import guppy
from guppy.module import GuppyModule
from tests.error.util import NonBool

module = GuppyModule("test")
module.load(tests.error.util)


@guppy(module)
def foo(x: NonBool) -> int:
    return 1 if x else 0


module.compile()
