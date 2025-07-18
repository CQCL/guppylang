from guppylang import guppy
from guppylang.module import GuppyModule

@guppy.wasm_module("", 0)
class Foo:
    @guppy.wasm
    def foo(x: int) -> None: ...

@guppy
def main() -> None:
    mod = Foo(0)
    mod.foo(42)
    mod.discard()
    return

main.compile()
