"""EXPERIMENTAL: The `list` type"""

# ruff: noqa: E501
# mypy: disable-error-code="empty-body, misc, override, valid-type, no-untyped-def, type-arg"

from __future__ import annotations

from typing import TYPE_CHECKING, Generic

from guppylang.decorator import guppy
from guppylang.definition.custom import NoopCompiler
from guppylang.std._internal.checker import UnsupportedChecker
from guppylang.std._internal.compiler.list import (
    ListGetitemCompiler,
    ListLengthCompiler,
    ListPopCompiler,
    ListPushCompiler,
    ListSetitemCompiler,
)
from guppylang.std._internal.util import unsupported_op
from guppylang.std.option import Option  # noqa: TCH001
from guppylang.tys.builtin import list_type_def

if TYPE_CHECKING:
    from guppylang.std.lang import owned


T = guppy.type_var("T")
L = guppy.type_var("L", copyable=False, droppable=False)


@guppy.extend_type(list_type_def)
class list(Generic[T]):
    """Mutable sequence items with homogeneous types."""

    @guppy.custom(ListGetitemCompiler())
    def __getitem__(self: list[L], idx: int) -> L: ...

    @guppy.custom(ListSetitemCompiler())
    def __setitem__(self: list[L], idx: int, value: L @ owned) -> None: ...

    @guppy.custom(ListLengthCompiler())
    def __len__(self: list[L]) -> int: ...

    @guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
    def __new__(x): ...

    @guppy.custom(NoopCompiler())  # TODO: define via Guppy source instead
    def __iter__(self: list[L] @ owned) -> list[L]: ...

    @guppy.hugr_op(unsupported_op("pop"))
    def __next__(self: list[L] @ owned) -> Option[tuple[L, list[L]]]: ...  # type: ignore[type-arg]

    @guppy.custom(ListPushCompiler())
    def append(self: list[L], item: L @ owned) -> None: ...

    @guppy.custom(ListPopCompiler())
    def pop(self: list[L]) -> L: ...
