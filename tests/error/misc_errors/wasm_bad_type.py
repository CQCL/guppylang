from guppylang import guppy
from guppylang.std.quantum import qubit


@guppy.wasm_module("", 0)
class Foo:
    @guppy.wasm
    def foo(self: "Foo", x: qubit) -> qubit: ...

@guppy
def main() -> qubit:
    mod = Foo(0)
    q = mod.foo(qubit())
    mod.discard
    return q

main.compile()
