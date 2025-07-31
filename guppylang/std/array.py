"""Utilities for fixed-size arrays, denoted `array[T, n]`, for element type `T` and
compile-time constant size `n`.

See `frozenarray[T, n]` for an immutable version of the `array[T, n]` type.
"""

# mypy: disable-error-code="empty-body, misc, override, valid-type, no-untyped-def"

from __future__ import annotations

import builtins
from types import GeneratorType
from typing import TYPE_CHECKING, Generic, TypeVar, no_type_check

from guppylang.decorator import custom_function, guppy
from guppylang.definition.custom import CopyInoutCompiler
from guppylang.std._internal.checker import ArrayCopyChecker, NewArrayChecker
from guppylang.std._internal.compiler.array import (
    ArrayGetitemCompiler,
    ArrayIterAsertAllUsedCompiler,
    ArraySetitemCompiler,
    NewArrayCompiler,
)
from guppylang.std._internal.compiler.frozenarray import FrozenarrayGetitemCompiler
from guppylang.std.iter import SizedIter
from guppylang.std.option import Option, nothing, some
from guppylang.tys.builtin import array_type_def, frozenarray_type_def

if TYPE_CHECKING:
    from guppylang.std.lang import owned


T = guppy.type_var("T")
L = guppy.type_var("L", copyable=False, droppable=False)
n = guppy.nat_var("n")

_T = TypeVar("_T")
_n = TypeVar("_n")


@guppy.extend_type(array_type_def)
class array(builtins.list[_T], Generic[_T, _n]):
    """Sequence of homogeneous values with statically known fixed length."""

    @custom_function(ArrayGetitemCompiler())
    def __getitem__(self: array[L, n], idx: int) -> L: ...

    @custom_function(ArraySetitemCompiler())
    def __setitem__(self: array[L, n], idx: int, value: L @ owned) -> None: ...

    @guppy
    @no_type_check
    def __len__(self: array[L, n]) -> int:
        return n

    @custom_function(NewArrayCompiler(), NewArrayChecker(), higher_order_value=False)
    def __new__(): ...

    # `__new__` will be overwritten below to provide actual runtime behaviour for
    # comptime. We still need to hold on to a reference to the Guppy function so
    # `@guppy.extend_type` can find it
    __new_guppy__ = __new__

    @guppy
    @no_type_check
    def __iter__(self: array[L, n] @ owned) -> SizedIter[ArrayIter[L, n], n]:
        return SizedIter(ArrayIter(self, 0))

    @custom_function(CopyInoutCompiler(), ArrayCopyChecker())
    def copy(self: array[T, n]) -> array[T, n]: ...

    def __new__(cls, *args: _T) -> builtins.list[_T]:  # type: ignore[no-redef]
        # Runtime array constructor that is used for comptime. We return an actual list
        # in line with the comptime unpacking logic that turns arrays into lists.
        if len(args) == 1 and isinstance(args[0], GeneratorType):
            return list(args[0])
        return [*args]


@guppy.struct
class ArrayIter(Generic[L, n]):
    """Iterator over arrays."""

    xs: array[L, n]
    i: int

    @guppy
    @no_type_check
    def __next__(
        self: ArrayIter[L, n] @ owned,
    ) -> Option[tuple[L, ArrayIter[L, n]]]:
        if self.i < int(n):
            elem = _array_unsafe_getitem(self.xs, self.i)
            return some((elem, ArrayIter(self.xs, self.i + 1)))
        self._assert_all_used()
        return nothing()

    @custom_function(ArrayIterAsertAllUsedCompiler())
    def _assert_all_used(self: ArrayIter[L, n] @ owned) -> None: ...


@custom_function(ArrayGetitemCompiler())
def _array_unsafe_getitem(xs: array[L, n], idx: int) -> L: ...


@guppy.extend_type(frozenarray_type_def)
class frozenarray(Generic[T, n]):
    """An immutable array of fixed static size."""

    @custom_function(FrozenarrayGetitemCompiler())
    def __getitem__(self: frozenarray[T, n], item: int) -> T: ...  # type: ignore[type-arg]

    @guppy
    @no_type_check
    def __len__(self: frozenarray[T, n]) -> int:
        return n

    @guppy
    @no_type_check
    def __iter__(self: frozenarray[T, n]) -> SizedIter[FrozenarrayIter[T, n], n]:
        return SizedIter(FrozenarrayIter(self, 0))

    @guppy
    @no_type_check
    def mutable_copy(self: frozenarray[T, n]) -> array[T, n]:
        """Creates a mutable copy of this array."""
        return array(x for x in self)


@guppy.struct
class FrozenarrayIter(Generic[T, n]):
    """Iterator for frozenarrays."""

    xs: frozenarray[T, n]  # type: ignore[type-arg]
    i: int

    @guppy
    @no_type_check
    def __next__(
        self: FrozenarrayIter[T, n],
    ) -> Option[tuple[T, FrozenarrayIter[T, n]]]:
        if self.i < int(n):
            return some((self.xs[self.i], FrozenarrayIter(self.xs, self.i + 1)))
        return nothing()
