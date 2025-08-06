from guppylang import guppy

@guppy.gpu_module("", 0)
class MyClass:
    @guppy.wasm
    def foo(self: "MyClass", x: int) -> None:
        return

@guppy
def bar(x: int) -> None:
    mc = MyClass()
    mc.foo(x)
    mc.discard()
