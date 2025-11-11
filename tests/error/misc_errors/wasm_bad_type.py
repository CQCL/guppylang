from guppylang import guppy
from guppylang_internals.decorator import wasm, wasm_module
from guppylang.std.quantum import qubit


@wasm_module("arith.wasm")
class Foo:
    @wasm
    def two(self: "Foo", x: qubit) -> qubit: ...

@guppy
def main() -> qubit:
    mod = Foo(0)
    q = mod.two(qubit())
    mod.discard
    return q

main.compile()
