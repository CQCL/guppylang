from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit
from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")
module.load(qubit)

T = guppy.type_var("T", copyable=False, droppable=True, module=module)


@guppy(module)
def foo(x: T @ owned) -> T:
    return x


@guppy(module)
def main() -> None:
    f = foo[qubit]


module.compile()
