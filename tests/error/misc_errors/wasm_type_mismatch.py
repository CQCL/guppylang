from guppylang import guppy
from guppylang_internals.decorator import wasm, wasm_module
from guppylang.module import GuppyModule

@wasm_module("arith.wasm")
class Foo:
    @wasm
    def add(self: "Foo", x: int, y: int, z: int) -> int: ...

@guppy
def main() -> bool:
    f = Foo(0)
    return f.add(1, 2)

main.compile()
