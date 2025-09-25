from guppylang.decorator import guppy
import pytest


def test_def():
    @guppy.protocol
    class MyProto[T]:
        @guppy.declare
        def foo(self: "MyProto", x: T) -> str: ...

    MyProto.compile()


@pytest.mark.skip("TODO: Enable once full implementation is done")
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
