"""Utilities for iteration over collections of values."""

# mypy: disable-error-code="empty-body, misc, override, valid-type, no-untyped-def"

from __future__ import annotations

from typing import TYPE_CHECKING, Any, no_type_check

from guppylang.decorator import guppy
from guppylang.definition.custom import NoopCompiler
from guppylang.std._internal.checker import RangeChecker
from guppylang.std.option import Option, nothing, some
from guppylang.tys.builtin import sized_iter_type_def

if TYPE_CHECKING:
    from guppylang.std.lang import owned


L = guppy.type_var("L", copyable=False, droppable=False)
n = guppy.nat_var("n")


@guppy.extend_type(sized_iter_type_def)
class SizedIter:
    """A wrapper around an iterator type `L` promising that the iterator will yield
    exactly `n` values.

    Annotating an iterator with an incorrect size is undefined behaviour.
    """

    def __class_getitem__(cls, item: Any) -> type:
        # Dummy implementation to allow subscripting of the `SizedIter` type in
        # positions that are evaluated by the Python interpreter
        return cls

    @guppy.custom(NoopCompiler())
    def __new__(iterator: L @ owned) -> SizedIter[L, n]:  # type: ignore[type-arg]
        """Casts an iterator into a `SizedIter`."""

    @guppy.custom(NoopCompiler())
    def unwrap_iter(self: SizedIter[L, n] @ owned) -> L:
        """Extracts the actual iterator."""

    @guppy.custom(NoopCompiler())
    def __iter__(self: SizedIter[L, n] @ owned) -> SizedIter[L, n]:  # type: ignore[type-arg]
        """Dummy implementation making sized iterators iterable themselves."""


@guppy.struct
class Range:
    next: int
    stop: int

    @guppy
    def __iter__(self: Range) -> Range:
        return self

    @guppy
    @no_type_check
    def __next__(self: Range) -> Option[tuple[int, Range]]:
        if self.next < self.stop:
            return some((self.next, Range(self.next + 1, self.stop)))
        return nothing()


@guppy.custom(checker=RangeChecker(), higher_order_value=False)
def range(stop: int) -> Range:
    """Limited version of python range().
    Only a single argument (stop/limit) is supported."""
