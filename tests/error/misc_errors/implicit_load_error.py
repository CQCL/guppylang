from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("test1")


@guppy(module)
def foo(x: float) -> int:
    return x


# Declaring an implicit module will load the explicit one above since it is in
# scope, so we will get the type error even though none of the modules were explicitly
# compiled

@guppy
def bar() -> None:
    pass

