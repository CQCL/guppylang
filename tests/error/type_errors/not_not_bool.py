from guppylang.decorator import guppy
from tests.error.util import NonBool


@guppy
def foo(x: NonBool) -> bool:
    return not x


guppy.compile(foo)
