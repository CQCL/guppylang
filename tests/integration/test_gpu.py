from guppylang_internals.decorator import gpu_module, gpu
from guppylang.decorator import guppy
from guppylang.std.builtins import nat, comptime
from guppylang.std.qsystem.gpu import spawn_gpu_contexts


def test_gpu_functions(validate):
    @gpu_module("module", "config")
    class MyModule:
        @gpu
        def add_one(self: "MyModule", x: int) -> int: ...

        @gpu(42)
        def foo(self: "MyModule", x: int, y: float) -> int: ...

    @guppy
    def main() -> int:
        [mod1, mod2] = spawn_gpu_contexts[2](MyModule)
        mod1 = MyModule(0)
        mod2 = MyModule(1)
        two = mod1.add_one(1)
        two2 = mod2.foo(two, 3.0)
        mod1.discard()
        mod2.discard()
        return two + two2
        return 2

    mod = main.compile()
    validate(mod)


def test_gpu_methods(validate):
    @gpu_module("module", "config")
    class MyModule:
        @gpu
        def foo(self: "MyModule") -> int: ...

        @guppy
        def bar(self: "MyModule", x: int) -> int:
            return x + 1

    @guppy
    def main() -> int:
        mod = MyModule(0)
        x = mod.foo()
        y = mod.bar(x)
        mod.discard()
        return x

    mod = main.compile()
    validate(mod)


def test_gpu_types(validate):
    n = guppy.nat_var("n")

    @gpu_module("", None)
    class MyModule:
        @gpu
        def foo(self: "MyModule", x: int, y: float, z: nat) -> None: ...

    @guppy
    def main() -> None:
        mod = MyModule(0)
        mod.foo(-1, 2.0, 3)
        mod.discard()
        return

    mod = main.compile()
    validate(mod)


def test_lookup_by_id(validate):
    from hugr.ops import AsExtOp

    @gpu_module("", None)
    class MyGpu:
        @gpu(1)
        def foo(self: "MyGpu") -> int: ...

    @guppy
    def main() -> int:
        c = MyGpu(0)
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
    assert not "lookup_by_name" in ops

def test_lookup_by_name(validate):
    from hugr.ops import AsExtOp

    @gpu_module("", None)
    class MyGpu:
        @gpu
        def foo(self: "MyGpu") -> int: ...

    @guppy
    def main() -> int:
        c = MyGpu(0)
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
    assert not "lookup_by_id" in ops
