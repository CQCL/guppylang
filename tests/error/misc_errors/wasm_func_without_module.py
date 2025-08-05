from guppylang import guppy
from guppylang_internals.decorator import wasm, wasm_module

@wasm_module("", 0)
class Foo:
    @wasm
    def foo(x: int) -> None: ...

@guppy
def main() -> None:
    mod = Foo(0)
    mod.foo(42)
    mod.discard()
    return

main.compile()
