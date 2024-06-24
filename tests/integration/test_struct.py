from typing import Generic, TYPE_CHECKING

from guppylang.decorator import guppy
from guppylang.module import GuppyModule

if TYPE_CHECKING:
    from collections.abc import Callable


def test_basic_defs(validate):
    module = GuppyModule("module")

    @guppy.struct(module)
    class EmptyStruct:
        pass

    @guppy.struct(module)
    class OneMemberStruct:
        x: int

    @guppy.struct(module)
    class TwoMemberStruct:
        x: tuple[bool, int]
        y: float

    @guppy.struct(module)
    class DocstringStruct:
        """This is struct with a docstring!"""

        x: int

    @guppy(module)
    def main(
        a: EmptyStruct, b: OneMemberStruct, c: TwoMemberStruct, d: DocstringStruct
    ) -> None:
        EmptyStruct()
        OneMemberStruct(42)
        TwoMemberStruct((True, 0), 1.0)
        DocstringStruct(-1)

    validate(module.compile())


def test_backward_ref(validate):
    module = GuppyModule("module")

    @guppy.struct(module)
    class StructA:
        x: int

    @guppy.struct(module)
    class StructB:
        y: StructA

    @guppy(module)
    def main(a: StructA, b: StructB) -> None:
        StructB(a)

    validate(module.compile())


def test_forward_ref(validate):
    module = GuppyModule("module")

    @guppy.struct(module)
    class StructA:
        x: "StructB"

    @guppy.struct(module)
    class StructB:
        y: int

    @guppy(module)
    def main(a: StructA, b: StructB) -> None:
        StructA(b)

    validate(module.compile())


def test_generic(validate):
    module = GuppyModule("module")
    S = guppy.type_var(module, "S")
    T = guppy.type_var(module, "T")

    @guppy.struct(module)
    class StructA(Generic[T]):
        x: tuple[int, T]

    @guppy.struct(module)
    class StructC:
        a: StructA[int]
        b: StructA[list[bool]]
        c: "StructB[float, StructB[bool, int]]"

    @guppy.struct(module)
    class StructB(Generic[S, T]):
        x: S
        y: StructA[T]

    @guppy(module)
    def main(a: StructA[StructA[float]], b: StructB[bool, int], c: StructC) -> None:
        x = StructA((0, False))
        y = StructA((0, -5))
        StructA((0, x))
        StructB(x, a)
        StructC(y, StructA((0, [])), StructB(42.0, StructA((4, b))))

    validate(module.compile())


def test_higher_order(validate):
    module = GuppyModule("module")
    T = guppy.type_var(module, "T")

    @guppy.struct(module)
    class Struct(Generic[T]):
        x: T

    @guppy(module)
    def factory(mk_struct: "Callable[[int], Struct[int]]", x: int) -> Struct[int]:
        return mk_struct(x)

    @guppy(module)
    def main() -> None:
        factory(Struct, 42)

    validate(module.compile())
