from guppylang import guppy
from guppylang_internals.decorator import wasm, wasm_module
from guppylang.module import GuppyModule

@wasm_module("")
class Foo:
    @wasm
    def foo(self: "Foo") -> bool: ...

@guppy
def main() -> bool:
    f = Foo(0)
    return f.foo()

main.compile()
