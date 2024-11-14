from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.quantum import qubit

module = GuppyModule("test")
module.load(qubit)


@guppy.struct(module)
class MyStruct:
    x: int
    q: qubit


@guppy(module)
def foo(s: MyStruct) -> tuple[MyStruct, bool]:
    t = s
    t.x += 1
    # People would expect `t.x == s.x`, but we can't do that
    # using the current tuple semantics
    return t, t.x == s.x


module.compile()
