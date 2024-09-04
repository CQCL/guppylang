import tests.error.util
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from tests.error.util import NonBool

module = GuppyModule("test")
module.load_all(tests.error.util)


@guppy(module)
def foo(x: bool, y: NonBool) -> bool:
    return x or y


module.compile()
