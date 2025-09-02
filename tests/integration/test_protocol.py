from guppylang.decorator import guppy

from typing import Protocol

def test_basic(validate):

    @guppy.struct
    class MyProto(Protocol):

        @guppy.declare
        def foo(self: "MyProto", x: int) -> str: ...

    @guppy.struct
    class MyType:

        @guppy
        def foo(self: "MyType", x: int) -> str:
            return str(x)

    @guppy 
    def bar(a: MyProto) -> str:
        return a.foo(42)

    validate(bar.compile())

