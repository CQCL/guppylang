from abc import ABC
from dataclasses import dataclass, field

from guppylang.checker.core import FieldAccess, Place, PlaceId, Variable
from guppylang.definition.common import CompiledDef, DefId
from guppylang.error import InternalGuppyError
from guppylang.hugr_builder.hugr import DFContainingNode, Hugr, OutPortV
from guppylang.tys.ty import StructType

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

    def __getitem__(self, place: Place) -> OutPortV:
        """Constructs a port for a local place in this DFG.

        Note that this mutates the Hugr since we might need to pack or unpack some
        tuples to obtain a port for places that involve struct fields.
        """
        # First check, if we already have a wire for this place
        if place.id in self.locals:
            return self.locals[place.id]
        # Otherwise, our only hope is that it's a struct value that we can rebuild by
        # packing the wires of its constituting fields
        if not isinstance(place.ty, StructType):
            raise InternalGuppyError(f"Couldn't obtain a port for `{place}`")
        children = [FieldAccess(place, field, None) for field in place.ty.fields]
        child_ports = [self[child] for child in children]
        port = self.graph.add_make_tuple(child_ports, self.node).out_port(0)
        for child in children:
            if child.ty.linear:
                self.locals.pop(child.id)
        self.locals[place.id] = port
        return port

    def __setitem__(self, place: Place, port: OutPortV) -> None:
        # When assigning a struct value, we immediately unpack it recursively and only
        # store the leaf wires.
        is_return = isinstance(place, Variable) and is_return_var(place.name)
        if isinstance(place.ty, StructType) and not is_return:
            unpack = self.graph.add_unpack_tuple(port, self.node)
            for field, field_port in zip(
                place.ty.fields, unpack.out_ports, strict=True
            ):
                self[FieldAccess(place, field, None)] = field_port
            # If we had a previous wire assigned to this place, we need forget about it.
            # Otherwise, we might use this old value when looking up the place later
            self.locals.pop(place.id, None)
        else:
            self.locals[place.id] = port

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
