"""Utilities for compile-time reflection."""

# mypy: disable-error-code="empty-body, misc, override, valid-type, no-untyped-def"

from guppylang.decorator import guppy
from guppylang.std._internal.checker import CallableChecker


@guppy.custom(checker=CallableChecker(), higher_order_value=False)
def callable(x): ...
