"""Utilities for compile-time reflection."""

# mypy: disable-error-code="empty-body, misc, override, valid-type, no-untyped-def"

from guppylang.decorator import custom_function
from guppylang.std._internal.checker import CallableChecker


@custom_function(checker=CallableChecker(), higher_order_value=False)
def callable(x): ...
