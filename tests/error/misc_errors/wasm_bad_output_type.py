from guppylang import guppy
from guppylang.module import GuppyModule

@guppy.wasm_module("", 0)
class Foo:
    @guppy.wasm
    def foo(self: "Foo") -> bool: ...

@guppy
def main() -> bool:
    f = Foo(0)
    return f.foo()

main.compile()
