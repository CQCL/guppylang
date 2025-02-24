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
    ctx: CompilerContext
    dfg: DFContainer
    node: AstNode

    allocated_objs: "dict[ObjectId, GuppyObject]" = field(default_factory=dict)
    unused_objs: "set[ObjectId]" = field(default_factory=set)


_STATE: TracingState | None = None
_GLOBALS: Globals | None = None


def get_tracing_state() -> TracingState:
    if _STATE is None:
        raise InternalGuppyError("Guppy tracing mode is not active")
    return _STATE


def get_tracing_globals() -> Globals:
    if _GLOBALS is None:
        raise InternalGuppyError("Guppy tracing mode is not active")
    return _GLOBALS


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


@contextmanager
def set_tracing_globals(globals: Globals) -> Iterator[None]:
    global _GLOBALS
    old_globals = _GLOBALS
    _GLOBALS = globals
    yield
    _GLOBALS = old_globals
