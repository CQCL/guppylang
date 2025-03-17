from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module1 = GuppyModule("test1")


@guppy(module1)
def foo(x: float) -> int:
    return x


module2 = GuppyModule("test2")

# Load invokes `check` on the imported module, so this will fail even though we don't
# compile `module2`
module2.load(foo)
