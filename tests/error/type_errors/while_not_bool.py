from guppylang.decorator import guppy
from tests.error.util import NonBool


@guppy
def foo(x: NonBool) -> int:
    while x:
        pass
    return 0


guppy.compile(foo)
