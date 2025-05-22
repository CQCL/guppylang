from guppylang.decorator import guppy
from guppylang.std.builtins import array
from guppylang.std.wasm import new_wasm
from hugr.hugr.render import DotRenderer

def test_wasm_functions(validate):
    @guppy.wasm_module("", 42)
    class MyWasm:

        @guppy.wasm
        def add_one(self: "MyWasm", x: int) -> int: ...

        @guppy.wasm
        def add_two(self: "MyWasm", x: int) -> int: ...
    @guppy
    def main() -> int:
        mod1 = MyWasm().unwrap()
        #mod2 = MyWasm().unwrap()
        two = mod1.add_one(1)
        #four = mod2.add_two(2)
        mod1.discard()
        #mod2.discard()
        return two + two

    with open("sus.hugr", 'w') as f:
        f.write(guppy.compile_module().package.to_str())
    mod = guppy.compile_module()
    with open("debug.hugr", 'w') as f:
        f.write(mod.package.to_str())
    #print(mod.module.to_model())
    #rr = DotRenderer().store(mod.module, "test")
    #print(mod)
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
        #y = mod.bar(x)
        mod.discard()
        return x

    mod = guppy.compile_module()
    validate(mod)

def test_wasm_types(validate):
    @guppy.wasm_module("", 3)
    class MyWasm:
        @guppy.wasm
        def foo(self: "MyWasm", x: tuple[int, array[float]], y: bool) -> None: ...

    @guppy
    def main() -> None:
        mod = MyWasm.unwrap()
        MyWasm.foo((42, array(1.0)), False)
        mod.discard()
        return

    mod = guppy.compile_module()
    validate(mod)
