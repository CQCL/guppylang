from typing import Generic

from guppylang.decorator import guppy
from guppylang.module import GuppyModule


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
        pass

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
        pass

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
        pass

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
    def main(a: StructA[StructA[float]], b: StructB[int, bool], c: StructC) -> None:
        pass

    validate(module.compile())
