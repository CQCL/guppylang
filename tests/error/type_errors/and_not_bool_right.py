from guppylang.decorator import guppy
from tests.error.util import NonBool


@guppy
def foo(x: bool, y: NonBool) -> bool:
    return x and y


guppy.compile(foo)
