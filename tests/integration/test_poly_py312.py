"""Tests Python 3.12 style generic syntax."""

from guppylang import array
from guppylang.decorator import guppy
from guppylang.std.lang import Copy, Drop, owned
from guppylang.std.num import nat
from guppylang.std.option import Option, nothing


def test_function(validate):
    @guppy
    def main[S, T](x: S @ owned, y: T @ owned) -> tuple[T, S]:
        return y, x

    validate(main.compile())


def test_struct(validate):
    @guppy.struct
    class MyStruct[S, T]:
        x: S
        y: T

    @guppy
    def main(s: MyStruct[int, float]) -> float:
        return s.x + s.y

    validate(main.compile())


def test_inner_frame(validate):
    """See https://github.com/CQCL/guppylang/issues/1116"""

    def make():
        @guppy.struct
        class MyStruct[T]:
            @guppy
            def foo(self: "MyStruct[int]") -> None:
                pass

        @guppy
        def main() -> None:
            MyStruct[int]().foo()

        return main

    validate(guppy.compile(make()))


def test_copy_bound(validate):
    @guppy.struct
    class MyStruct[T: Copy]:
        x: T

    @guppy
    def main[T: Copy](s: MyStruct[T]) -> tuple[T, T]:
        return s.x, s.x

    validate(main.compile())


def test_drop_bound(validate):
    @guppy.struct
    class MyStruct[T: Drop]:
        x: T

    @guppy
    def main[T: Drop](s: MyStruct[T] @ owned) -> None:
        pass

    validate(main.compile())


def test_copy_and_drop_bound(validate):
    @guppy.struct
    class MyStruct[T: (Copy, Drop)]:
        x: T

    @guppy
    def main[T: (Copy, Drop)](s1: MyStruct[T], s2: MyStruct[T]) -> tuple[T, T]:
        return s1.x, s1.x

    validate(main.compile())


def test_const_param(validate):
    @guppy.struct
    class MyStruct[T, n: nat]:
        xs: array[T, n]

    @guppy
    def main[T, n: nat](xs: array[T, n], s: MyStruct[T, n]) -> nat:
        return n

    validate(main.compile())


def test_mixed_legacy_params(validate):
    T = guppy.type_var("T", copyable=False, droppable=False)

    @guppy
    def main[S](x: S @ owned, y: T @ owned) -> tuple[T, S]:
        return y, x

    validate(main.compile())


def test_reference_inside(validate):
    @guppy
    def main[T: Drop]() -> None:
        x: Option[T] = nothing()
        nothing[T]()

    validate(main.compile())
