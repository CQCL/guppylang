from abc import ABC
from dataclasses import dataclass, field

from guppylang.checker.core import Place, PlaceId
from guppylang.definition.common import CompiledDef, DefId
from guppylang.hugr_builder.hugr import DFContainingNode, Hugr, OutPortV

CompiledGlobals = dict[DefId, CompiledDef]
CompiledLocals = dict[PlaceId, OutPortV]


@dataclass
class DFContainer:
    """A dataflow graph under construction.

    This class is passed through the entire compilation pipeline and stores the node
    whose dataflow child-graph is currently being constructed as well as all live local
    variables. Note that the variable map is mutated in-place and always reflects the
    current compilation state.
    """

    graph: Hugr
    node: DFContainingNode
    locals: CompiledLocals = field(default_factory=dict)

    def __setitem__(self, key: PlaceId, value: OutPortV) -> None:
        self.locals[key] = value

    def __contains__(self, item: Place) -> bool:
        return item in self.locals

    def __copy__(self) -> "DFContainer":
        # Make a copy of the var map so that mutating the copy doesn't
        # mutate our variable mapping
        return DFContainer(self.graph, self.node, self.locals.copy())


class CompilerBase(ABC):
    """Base class for the Guppy compiler."""

    graph: Hugr
    globals: CompiledGlobals

    def __init__(self, graph: Hugr, globals: CompiledGlobals) -> None:
        self.graph = graph
        self.globals = globals


def return_var(n: int) -> str:
    """Name of the dummy variable for the n-th return value of a function.

    During compilation, we treat return statements like assignments of dummy variables.
    For example, the statement `return e0, e1, e2` is treated like `%ret0 = e0 ; %ret1 =
    e1 ; %ret2 = e2`. This way, we can reuse our existing mechanism for passing of live
    variables between basic blocks."""
    return f"%ret{n}"


def is_return_var(x: str) -> bool:
    """Checks whether the given name is a dummy return variable."""
    return x.startswith("%ret")
