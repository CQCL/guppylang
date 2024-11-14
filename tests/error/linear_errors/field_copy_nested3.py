import guppylang.std.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit, measure


module = GuppyModule("test")
module.load_all(quantum)


@guppy.struct(module)
class MyStruct1:
    x: "MyStruct2"


@guppy.struct(module)
class MyStruct2:
    q: qubit


@guppy.declare(module)
def use(s: MyStruct2 @owned) -> None: ...


@guppy(module)
def foo(s: MyStruct1 @owned) -> qubit:
    use(s.x)
    return s.x.q


module.compile()
