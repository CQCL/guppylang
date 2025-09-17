from guppylang.decorator import guppy

def test_def(validate):

    @guppy.protocol
    class MyProto:

        @guppy.declare
        def foo(self: "MyProto", x: int) -> str: ...

    validate(MyProto.compile())


def test_basic(validate):

    @guppy.protocol
    class MyProto:

        @guppy.declare
        def foo(self: "MyProto", x: int) -> str: ...

    @guppy.struct
    class MyType:

        @guppy
        def foo(self: "MyType", x: int) -> str:
            return str(x)

    @guppy 
    def bar[M: MyProto](a: M) -> str:
        return a.foo(42)
    
    @guppy
    def main() -> str:
        mt = MyType()   
        return bar(mt)

    validate(main.compile())

