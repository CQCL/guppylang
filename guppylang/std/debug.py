"""Guppy standard module for debug functionality."""

# mypy: disable-error-code="empty-body, no-untyped-def"

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std import quantum
from guppylang.std._internal.debug import StateResultChecker

debug = GuppyModule("debug")
debug.load(quantum)


@guppy.custom(checker=StateResultChecker(), higher_order_value=False, module=debug)
def state_result(tag, *args) -> None:
    """Report the quantum state of the specified qubits.

    This is a debugging function that works only when the program is executed
    on a supported simulator.

    Args:
        tag: A string literal representing the tag of the result.
        args: The qubits whose quantum state is to be reported. The order they are given
        in corresponds to the order in which the state will be reported.
    """
