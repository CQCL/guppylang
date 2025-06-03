"""The string type."""

# mypy: disable-error-code="empty-body, misc, override, valid-type, no-untyped-def"

from __future__ import annotations

from guppylang.decorator import guppy
from guppylang.std._internal.checker import UnsupportedChecker
from guppylang.tys.builtin import string_type_def


@guppy.extend_type(string_type_def)
class str:
    """A string, i.e. immutable sequences of Unicode code points."""

    @guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
    def __new__(x): ...
