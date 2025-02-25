from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from guppylang.ast_util import AstNode
from guppylang.checker.core import Globals
from guppylang.compiler.core import CompilerContext, DFContainer
from guppylang.error import InternalGuppyError

if TYPE_CHECKING:
    from guppylang.tracing.object import GuppyObject, ObjectId


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
    unused_linear_objs: "dict[ObjectId, GuppyObject]" = field(default_factory=dict)

    @property
    def globals(self) -> Globals:
        return self.ctx.checked_globals


_STATE: TracingState | None = None


def get_tracing_state() -> TracingState:
    if _STATE is None:
        raise InternalGuppyError("Guppy tracing mode is not active")
    return _STATE


def tracing_active() -> bool:
    global _STATE
    return _STATE is not None


def reset_state() -> None:
    global _STATE
    _STATE = None


@contextmanager
def set_tracing_state(state: TracingState) -> Iterator[None]:
    global _STATE
    old_state = _STATE
    _STATE = state
    yield
    _STATE = old_state
