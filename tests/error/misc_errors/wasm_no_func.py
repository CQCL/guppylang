from guppylang import guppy
from guppylang_internals.decorator import wasm, wasm_module

@wasm_module("arith.wasm")
class MyWasm:
    @wasm
    def foo(self: "MyWasm") -> None: ...


@guppy
def main() -> None:
    mod = MyWasm(0)
    mod.foo()
    mod.discard()


main.compile()
