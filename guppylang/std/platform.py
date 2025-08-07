"""Platform functions."""

# mypy: disable-error-code="empty-body, misc, override, valid-type, no-untyped-def"

from __future__ import annotations

from typing import no_type_check

from guppylang_internals.decorator import custom_function
from guppylang_internals.std._internal.checker import (
    BarrierChecker,
    ExitChecker,
    PanicChecker,
    ResultChecker,
)


@custom_function(checker=ResultChecker(), higher_order_value=False)
def result(tag: str, value):
    """Report a result with the given tag and value.

    This is the primary way to report results from the program back to the user.
    On Quantinuum systems a single shot execution will return a list of pairs of
    (tag, value).

    Args:
        tag: The tag of the result. Must be a string literal
        value: The value of the result. Currently supported value types are `int`,
        `nat`, `float`, and `bool`.
    """


@custom_function(checker=PanicChecker(), higher_order_value=False)
def panic(msg: str, *args):
    """Panic, throwing an error with the given message, and immediately exit the
    program, aborting any subsequent shots.

    Return type is arbitrary, as this function never returns.

    Args:
        msg: The message to display. Must be a string literal.
        args: Arbitrary extra inputs, will not affect the message. Only useful for
        consuming linear values.
    """


@custom_function(checker=ExitChecker(), higher_order_value=False)
def exit(msg: str, signal: int, *args):
    """Exit, reporting the given message and signal, and immediately exit the
    program. Subsequent shots may still run.

    Return type is arbitrary, as this function never returns.

    On Quantinuum systems only signals in the range 1<=signal<=1000 are supported.

    Args:
        msg: The message to display. Must be a string literal.
        args: Arbitrary extra inputs, will not affect the message. Only useful for
        consuming linear values.
    """


@custom_function(checker=BarrierChecker(), higher_order_value=False)
@no_type_check
def barrier(*args) -> None:
    """Barrier to guarantee that all operations before the barrier are completed before
    operations after the barrier are started."""
