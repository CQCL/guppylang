from guppylang import guppy
from guppylang_internals.decorator import wasm, wasm_module
from guppylang.std.quantum import qubit


@wasm_module("", 0)
class Foo:
    @wasm
    def foo(self: "Foo", x: qubit) -> qubit: ...

@guppy
def main() -> qubit:
    mod = Foo(0)
    q = mod.foo(qubit())
    mod.discard
    return q

main.compile()
