from typing import Generic, Protocol
from guppylang.decorator import guppy


def test_def_legacy1():
    T = guppy.type_var("T")

    @guppy.protocol
    class MyProto(Generic[T]):
        @guppy.declare
        def foo(self: "MyProto", x: T) -> str: ...

    MyProto.compile()


def test_def_legacy2():
    T = guppy.type_var("T")

    @guppy.protocol
    class MyProto(Protocol[T]):
        @guppy.declare
        def foo(self: "MyProto", x: T) -> str: ...

    MyProto.compile()


def test_def_legacy3():
    @guppy.protocol
    class MyProto(Protocol):
        @guppy.declare
        def foo(self: "MyProto", x: int) -> str: ...

    MyProto.compile()
