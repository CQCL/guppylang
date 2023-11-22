from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Iterator

from guppy.ast_util import AstNode
from guppy.checker.core import Variable, CallableVariable
from guppy.gtypes import FunctionType
from guppy.hugr.hugr import OutPortV, DFContainingNode, Hugr


@dataclass
class PortVariable(Variable):
    """Represents a local variable in a dataflow graph.

    Local variables are associated with a port in the Hugr.
    """

    port: OutPortV

    def __init__(
        self,
        name: str,
        port: OutPortV,
        defined_at: Optional[AstNode],
        used: Optional[AstNode] = None,
    ) -> None:
        super().__init__(name, port.ty, defined_at, used)
        object.__setattr__(self, "port", port)


class CompiledVariable(ABC, Variable):
    """Abstract base class for compiled global module-level variables."""

    @abstractmethod
    def load(
        self, dfg: "DFContainer", graph: Hugr, globals: "CompiledGlobals", node: AstNode
    ) -> OutPortV:
        """Loads the variable as a value into a local dataflow graph."""


class CompiledFunction(CompiledVariable, CallableVariable):
    """Abstract base class a global module-level function."""

    ty: FunctionType

    @abstractmethod
    def compile_call(
        self,
        args: list[OutPortV],
        dfg: "DFContainer",
        graph: Hugr,
        globals: "CompiledGlobals",
        node: AstNode,
    ) -> list[OutPortV]:
        """Compiles a call to the function."""


CompiledGlobals = dict[str, CompiledVariable]
CompiledLocals = dict[str, PortVariable]


@dataclass
class DFContainer:
    """A dataflow graph under construction.

    This class is passed through the entire compilation pipeline and stores the node
    whose dataflow child-graph is currently being constructed as well as all live local
    variables. Note that the variable map is mutated in-place and always reflects the
    current compilation state.
    """

    node: DFContainingNode
    locals: CompiledLocals

    def __getitem__(self, item: str) -> PortVariable:
        return self.locals[item]

    def __setitem__(self, key: str, value: PortVariable) -> None:
        self.locals[key] = value

    def __iter__(self) -> Iterator[PortVariable]:
        return iter(self.locals.values())

    def __contains__(self, item: str) -> bool:
        return item in self.locals

    def __copy__(self) -> "DFContainer":
        # Make a copy of the var map so that mutating the copy doesn't
        # mutate our variable mapping
        return DFContainer(self.node, self.locals.copy())

    def get_var(self, name: str) -> Optional[PortVariable]:
        return self.locals.get(name, None)


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
