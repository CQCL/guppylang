from guppylang import GuppyModule
from guppylang.decorator import guppy
from guppylang.std.builtins import nat, array
from guppylang.std.qsystem.wasm import spawn_wasm_contexts

def test_wasm_functions(validate):
    @guppy.wasm_module("", 42)
    class MyWasm:
        @guppy.wasm
        def add_one(self: "MyWasm", x: int) -> int: ...

        @guppy.wasm
        def swap(self: "MyWasm", x: int, y: bool) -> tuple[bool, int]: ...

    @guppy
    def main() -> int:
        [mod1, mod2] = spawn_wasm_contexts(2, MyWasm)
        two = mod1.add_one(1)
        b, two2 = mod2.swap(two, True)
        mod1.discard()
        mod2.discard()
        return two + two2
        return 2

    mod = main.compile()
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
        mod = MyWasm(0)
        x = mod.foo()
        y = mod.bar(x)
        mod.discard()
        return x

    mod = main.compile()
    validate(mod)


def test_wasm_types(validate):
    n = guppy.nat_var("n")

    @guppy.wasm_module("", 3)
    class MyWasm:
        @guppy.wasm
        def foo(self: "MyWasm", x: tuple[int, tuple[nat, float]], y: bool) -> None: ...

    @guppy
    def main() -> None:
        mod = MyWasm(0)
        mod.foo((0, (1, 2.0)), False)
        mod.discard()
        return

    mod = main.compile()
    validate(mod)


def test_wasm_guppy_module(validate):
    @guppy.wasm_module("", 42)
    class MyWasm:
        @guppy.wasm
        def add_one(self: "MyWasm", x: int) -> int: ...

        @guppy.wasm
        def swap(self: "MyWasm", x: int, y: bool) -> tuple[bool, int]: ...

    @guppy
    def main() -> int:
        [mod1, mod2] = spawn_wasm_contexts(2, MyWasm)
        two = mod1.add_one(1)
        b, two2 = mod2.swap(two, True)
        mod1.discard()
        mod2.discard()
        return two + two2

    mod = main.compile()
    validate(mod)
