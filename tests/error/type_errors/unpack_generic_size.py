from guppylang import GuppyModule, guppy
from guppylang.std.builtins import array


module = GuppyModule('main')
n = guppy.nat_var("n", module=module)


@guppy(module)
def foo(xs: array[int, n]) -> int:
    a, *bs = xs
    return a


module.compile()
