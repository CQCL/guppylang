from guppylang import guppy
from guppylang_internals.decorator import wasm, wasm_module
from guppylang.std.builtins import nat
from guppylang.std.qsystem.wasm import spawn_wasm_contexts


def test_wasm_functions(validate):
    @wasm_module("module.wasm")
    class MyWasm:
        @wasm
        def add_one(self: "MyWasm", x: int) -> int: ...

        @wasm
        def swap(self: "MyWasm", x: int, y: float) -> tuple[float, int]: ...

    @guppy
    def main() -> int:
        [mod1, mod2] = spawn_wasm_contexts(2, MyWasm)
        two = mod1.add_one(1)
        _, two2 = mod2.swap(two, 3.0)
        mod1.discard()
        mod2.discard()
        return two + two2
        return 2

    mod = main.compile()
    validate(mod)


def test_wasm_methods(validate):
    @wasm_module("module.wasm")
    class MyWasm:
        @wasm
        def foo(self: "MyWasm") -> int: ...

        @guppy
        def bar(self: "MyWasm", x: int) -> int:
            return x + 1

    @guppy
    def main() -> int:
        mod = MyWasm(1)
        x = mod.foo()
        y = mod.bar(x)
        mod.discard()
        return x

    mod = main.compile()
    validate(mod)


def test_wasm_types(validate):
    n = guppy.nat_var("n")

    @wasm_module("")
    class MyWasm:
        @wasm(42)
        def foo(self: "MyWasm", x: tuple[int, tuple[nat, float]], y: int) -> None: ...

    @guppy
    def main() -> None:
        mod = MyWasm(1)
        mod.foo((0, (1, 2.0)), 3)
        mod.discard()
        return

    mod = main.compile()
    validate(mod)


def test_wasm_guppy_module(validate):
    @wasm_module("")
    class MyWasm:
        @wasm
        def add_one(self: "MyWasm", x: int) -> int: ...

        @wasm(1)
        def swap(self: "MyWasm", x: int, y: float) -> tuple[float, int]: ...

    @guppy
    def main() -> int:
        [mod1, mod2] = spawn_wasm_contexts(2, MyWasm)
        two = mod1.add_one(1)
        _, two2 = mod2.swap(two, 3.0)
        mod1.discard()
        mod2.discard()
        return two + two2

    mod = main.compile()
    validate(mod)


def test_lookup_by_id(validate):
    from hugr.ops import AsExtOp

    @wasm_module("")
    class MyWasm:
        @wasm(1)
        def foo(self: "MyWasm") -> int: ...

    @guppy
    def main() -> int:
        c = MyWasm(1)
        x = c.foo()
        c.discard()
        return x

    mod = main.compile()
    validate(mod)

    ops = set()
    for hugr in mod.modules[:]:
        for _, node in hugr.nodes():
            match node.op:
                case AsExtOp():
                    ops |= {node.op.op_def().name}
                case _:
                    pass
    assert "lookup_by_id" in ops
    assert "lookup_by_name" not in ops


def test_lookup_by_name(validate):
    from hugr.ops import AsExtOp

    @wasm_module("")
    class MyWasm:
        @wasm
        def foo(self: "MyWasm") -> int: ...

    @guppy
    def main() -> int:
        c = MyWasm(1)
        x = c.foo()
        c.discard()
        return x

    mod = main.compile()
    validate(mod)

    ops = set()
    for hugr in mod.modules[:]:
        for _, node in hugr.nodes():
            match node.op:
                case AsExtOp():
                    ops |= {node.op.op_def().name}
                case _:
                    pass
    assert "lookup_by_name" in ops
    assert "lookup_by_id" not in ops
