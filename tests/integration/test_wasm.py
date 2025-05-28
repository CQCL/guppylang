from guppylang.decorator import guppy
from guppylang.std.builtins import nat

def test_wasm_functions(validate):
    @guppy.wasm_module("", 42)
    class MyWasm:

        @guppy.wasm
        def add_one(self: "MyWasm", x: int) -> int: ...

        @guppy.wasm
        def swap(self: "MyWasm", x: int, y: bool) -> tuple[bool, int]: ...
    @guppy
    def main() -> int:
        mod1 = MyWasm().unwrap()
        mod2 = MyWasm().unwrap()
        two = mod1.add_one(1)
        b, two2 = mod2.swap(two, True)
        mod1.discard()
        mod2.discard()
        return two + two2

    mod = guppy.compile_module()
    validate(mod)

def test_wasm_methods(validate):
    @guppy.wasm_module("", 2)
    class MyWasm:
        @guppy.wasm
        def foo(self: "MyWasm") -> int: ...

        @guppy
        def bar(self: "MyWasm", x: int) -> int:
            return x + 1

    @guppy
    def main() -> int:
        mod = MyWasm().unwrap()
        x = mod.foo()
        y = mod.bar(x)
        mod.discard()
        return x

    mod = guppy.compile_module()
    validate(mod)

def test_wasm_types(validate):
    n = guppy.nat_var("n")

    @guppy.wasm_module("", 3)
    class MyWasm:
        @guppy.wasm
        def foo(self: "MyWasm", x: tuple[int, tuple[nat, float]], y: bool) -> None: ...

    @guppy
    def main() -> None:
        mod = MyWasm().unwrap()
        mod.foo((0, (1, 2.0)), False)
        mod.discard()
        return

    mod = guppy.compile_module()
    validate(mod)
