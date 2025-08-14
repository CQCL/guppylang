from typing import Generic

from guppylang import guppy


def test_implicit_self(validate):
    @guppy.struct
    class MyStruct:
        @guppy
        def foo(self) -> None:
            pass

    @guppy
    def main(s: MyStruct) -> None:
        s.foo()

    validate(main.compile())


def test_implicit_self_generic(validate):
    T = guppy.type_var("T")
    U = guppy.type_var("U")

    @guppy.struct
    class MyStruct(Generic[T, U]):
        x: T
        y: U

        @guppy
        def foo(self, a: U) -> T:
            return self.x

    @guppy
    def main(s: MyStruct[int, float]) -> int:
        return s.foo(1.5)

    validate(main.compile())


def test_more_generic(validate):
    T = guppy.type_var("T")
    U = guppy.type_var("U")

    @guppy.struct
    class MyStruct(Generic[T]):
        c: bool
        x: T

        @guppy
        def foo(self, a: T, b: U) -> tuple[T, U]:
            if self.c:
                a = self.x
            return a, b

    @guppy
    def main(s: MyStruct[int]) -> int:
        a, _ = s.foo(42, True)
        a, _ = s.foo(a, 1.5)
        a, b = s.foo(a, s.x)
        return a + b

    validate(main.compile())
