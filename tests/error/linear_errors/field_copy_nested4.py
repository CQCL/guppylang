import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import qubit, measure


module = GuppyModule("test")
module.load(quantum)


@guppy.struct(module)
class MyStruct1:
    x: "MyStruct2"


@guppy.struct(module)
class MyStruct2:
    q: qubit


@guppy.declare(module)
def use(s: MyStruct1) -> None: ...


@guppy(module)
def foo(s: MyStruct1) -> MyStruct1:
    use(s)
    return s


module.compile()
