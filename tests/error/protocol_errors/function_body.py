from guppylang.decorator import guppy


@guppy.protocol
class MyProto:
    @guppy.declare
    def foo(self: "MyProto", x: int) -> str: 
        return "abcdef"


MyProto.compile()
