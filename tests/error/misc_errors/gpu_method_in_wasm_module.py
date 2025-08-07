from guppylang import guppy

@guppy.wasm_module("")
class MyClass:
    @guppy.gpu
    def foo(self: "MyClass", x: int) -> None:
        return

@guppy
def bar(x: int) -> None:
    mc = MyClass()
    mc.foo(x)
    mc.discard()
