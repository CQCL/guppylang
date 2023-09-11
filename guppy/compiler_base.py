from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator, Optional, Any, NamedTuple, Union

from guppy.ast_util import AstNode
from guppy.guppy_types import GuppyType, FunctionType, TupleType, SumType
from guppy.hugr.hugr import OutPortV, Hugr, DFContainingNode


ValueName = str
TypeName = str


@dataclass
class RawVariable:
    """Class holding data associated with a variable.

    Besides the name and type, we also store an AST node where the variable was defined.
    """

    name: ValueName
    ty: GuppyType
    defined_at: Optional[AstNode]

    def __lt__(self, other: Any) -> bool:
        # We define an ordering on variables that is used to determine in which order
        # they are outputted from basic blocks. We need to output linear variables at
        # the end, so we do a lexicographic ordering of linearity and name, exploiting
        # the fact that `False < True` in Python.
        if not isinstance(other, Variable):
            return NotImplemented
        return (self.ty.linear, self.name) < (other.ty.linear, other.name)


@dataclass
class Variable(RawVariable):
    """Represents a concrete variable during compilation.

    Compared to a `RawVariable`, each variable corresponds to a Hugr port.
    """

    port: OutPortV
    used: Optional[AstNode] = None

    def __init__(self, name: str, port: OutPortV, defined_at: Optional[AstNode]):
        super().__init__(name, port.ty, defined_at)
        object.__setattr__(self, "port", port)


# A dictionary mapping names to live variables
VarMap = dict[ValueName, Variable]


@dataclass
class DFContainer:
    """A dataflow graph under construction.

    This class is passed through the entire compilation pipeline and stores the node
    whose dataflow child-graph is currently being constructed as well as all live
    variables. Note that the variable map is mutated in-place and always reflects the
    current compilation state.
    """

    node: DFContainingNode
    variables: VarMap

    def __getitem__(self, item: str) -> Variable:
        return self.variables[item]

    def __setitem__(self, key: str, value: Variable) -> None:
        self.variables[key] = value

    def __iter__(self) -> Iterator[Variable]:
        return iter(self.variables.values())

    def __contains__(self, item: str) -> bool:
        return item in self.variables

    def __copy__(self) -> "DFContainer":
        # Make a copy of the var map so that mutating the copy doesn't
        # mutate our variable mapping
        return DFContainer(self.node, self.variables.copy())

    def get_var(self, name: str) -> Optional[Variable]:
        return self.variables.get(name, None)


@dataclass
class GlobalVariable(ABC, RawVariable):
    """Represents a global module-level variable."""

    @abstractmethod
    def load(
        self, graph: Hugr, parent: DFContainingNode, globals: "Globals", node: AstNode
    ) -> OutPortV:
        """Loads the global variable as a value into a local dataflow graph."""


@dataclass
class GlobalFunction(GlobalVariable, ABC):
    """Represents a global module-level function."""

    ty: FunctionType
    call_compiler: "CallCompiler"

    def compile_call(
        self,
        args: list[OutPortV],
        parent: DFContainingNode,
        graph: Hugr,
        globals: "Globals",
        node: AstNode,
    ) -> list[OutPortV]:
        """Utility method that invokes the local `CallCompiler` to compile a function
        call"""
        cc = self.call_compiler
        cc.parent = parent
        cc.graph = graph
        cc.globals = globals
        cc.node = node
        cc.func = self
        return cc.compile(args)


class Globals(NamedTuple):
    """Collection of names that are available on module-level.

    Separately stores names that are bound to values (i.e. module-level functions or
    constants), to types, or to instance functions belonging to types.
    """

    values: dict[ValueName, GlobalVariable]
    types: dict[TypeName, type[GuppyType]]
    instance_funcs: dict[tuple[TypeName, ValueName], GlobalFunction]

    @staticmethod
    def default() -> "Globals":
        """Generates a `Globals` instance that is populated with all core types"""
        tys: dict[str, type[GuppyType]] = {
            FunctionType.name: FunctionType,
            TupleType.name: TupleType,
            SumType.name: SumType,
        }
        return Globals({}, tys, {})

    def get_instance_func(self, ty: GuppyType, name: str) -> Optional[GlobalFunction]:
        """Looks up an instance function with a given name for a type"""
        return self.instance_funcs.get((ty.name, name), None)

    def __or__(self, other: "Globals") -> "Globals":
        return Globals(
            self.values | other.values,
            self.types | other.types,
            self.instance_funcs | other.instance_funcs,
        )

    def __ior__(self, other: "Globals") -> "Globals":
        self.values.update(other.values)
        self.types.update(other.types)
        self.instance_funcs.update(other.instance_funcs)
        return self


class CompilerBase(ABC):
    """Base class for the Guppy compiler."""

    graph: Hugr
    globals: Globals

    def __init__(self, graph: Hugr, globals: Globals) -> None:
        self.graph = graph
        self.globals = globals


class CallCompiler(ABC):
    """Abstract base class for function call compilers."""

    graph: Hugr
    globals: Globals
    func: GlobalFunction
    parent: DFContainingNode
    node: AstNode

    @abstractmethod
    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        """Compiles a function call with the given argument ports.

        Returns a row of output ports that are returned by the function.
        """
        ...


def return_var(n: int) -> str:
    """Name of the dummy variable for the n-th return value of a function.

    During compilation, we treat return statements like assignments of dummy variables.
    For example, the statement `return e0, e1, e2` is treated like `%ret0 = e0 ; %ret1 =
    e1 ; %ret2 = e2`. This way, we can reuse our existing mechanism for passing of live
    variables between basic blocks."""
    return f"%ret{n}"
