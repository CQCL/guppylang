from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from guppylang.ast_util import AstNode
from guppylang.checker.core import Globals
from guppylang.compiler.core import CompilerContext, DFContainer
from guppylang.error import InternalGuppyError

if TYPE_CHECKING:
    from guppylang.tracing.object import GuppyObject, GuppyObjectId


@dataclass
class TracingState:
    """Internal state that is used during the tracing phase of comptime functions."""

    #: Reference to the global compilation context.
    ctx: CompilerContext

    #: The current dataflow graph under construction.
    dfg: DFContainer

    #: An AST node capturing the code block that is currently being traced
    node: AstNode

    #: Set of all allocated linear GuppyObjects where the `used` flag is not set,
    #: indexed by their id. This is used to detect linearity violations.
    unused_linear_objs: "dict[GuppyObjectId, GuppyObject]" = field(default_factory=dict)

    @property
    def globals(self) -> Globals:
        return self.ctx.checked_globals


_STATE: TracingState | None = None


def reset_state() -> None:
    """Resets the tracing state to be undefined."""
    global _STATE
    _STATE = None


def tracing_active() -> bool:
    """Checks if the tracing mode is currently active."""
    global _STATE
    return _STATE is not None


def get_tracing_state() -> TracingState:
    """Returns the current tracing state.

    Raises an `InternalGuppyError` if the tracing mode is currently not active.
    """
    if _STATE is None:
        raise InternalGuppyError("Guppy tracing mode is not active")
    return _STATE


@contextmanager
def set_tracing_state(state: TracingState) -> Iterator[None]:
    """Context manager to update tracing state for the duration of a code block."""
    global _STATE
    old_state = _STATE
    _STATE = state
    yield
    _STATE = old_state
