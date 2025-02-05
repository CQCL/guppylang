from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import cast

from hugr import Wire, ops
from hugr.build.dfg import DP, DefinitionBuilder, DfBase

from guppylang.checker.core import FieldAccess, Globals, Place, PlaceId, Variable
from guppylang.definition.common import CheckedDef, CompilableDef, CompiledDef, DefId
from guppylang.definition.ty import TypeDef
from guppylang.definition.value import CallReturnWires, CompiledCallableDef
from guppylang.error import InternalGuppyError
from guppylang.tys.ty import StructType, Type

CompiledLocals = dict[PlaceId, Wire]


class CustomCompilerMethod(ABC):
    """
    Abstract base class for functions in custom compilers that should only be
    constructed once to avoid inlining.
    """

    @abstractmethod
    def call(self, *args) -> CallReturnWires: ...


class CompiledContext:
    """Compilation context containing all available definitions.

    Maintains a `worklist` of definitions which have been used by other compiled code
    (i.e. `compile_outer` has been called) but have not yet been compiled/lowered
    themselves (i.e. `compile_inner` has not yet been called).
    """

    module: DefinitionBuilder[ops.Module]
    checked: dict[DefId, CheckedDef]
    compiled: dict[DefId, CompiledDef]
    worklist: set[DefId]
    compiler_methods: dict[str, CustomCompilerMethod]

    checked_globals: Globals

    def __init__(
        self,
        checked: dict[DefId, CheckedDef],
        module: DefinitionBuilder[ops.Module],
        checked_globals: Globals,
    ) -> None:
        self.module = module
        self.checked = checked
        self.worklist = set()
        self.compiled = {}
        self.compiler_methods = {}
        self.checked_globals = checked_globals

    def build_compiled_def(self, def_id: DefId) -> CompiledDef:
        """Returns the compiled definitions corresponding to the given ID.

        Might mutate the current Hugr if this definition has never been compiled before.
        """
        if def_id not in self.compiled:
            defn = self.checked[def_id]
            self.compiled[def_id] = self._compile(defn)
            self.worklist.add(def_id)
        return self.compiled[def_id]

    def _compile(self, defn: CheckedDef) -> CompiledDef:
        if isinstance(defn, CompilableDef):
            return defn.compile_outer(self.module)
        return defn

    def compile(self, defn: CheckedDef) -> None:
        """Compiles the given definition and all of its dependencies into the current
        Hugr."""
        if defn.id in self.compiled:
            return

        self.compiled[defn.id] = self._compile(defn)
        self.worklist.add(defn.id)
        while self.worklist:
            next_id = self.worklist.pop()
            next_def = self.build_compiled_def(next_id)
            next_def.compile_inner(self)

    def get_instance_func(
        self, ty: Type | TypeDef, name: str
    ) -> CompiledCallableDef | None:
        checked_func = self.checked_globals.get_instance_func(ty, name)
        if checked_func is None:
            return None
        compiled_func = self.build_compiled_def(checked_func.id)
        assert isinstance(compiled_func, CompiledCallableDef)
        return compiled_func


@dataclass
class DFContainer:
    """A dataflow graph under construction.

    This class is passed through the entire compilation pipeline and stores a builder
    for the dataflow child-graph currently being constructed as well as all live local
    variables. Note that the variable map is mutated in-place and always reflects the
    current compilation state.
    """

    builder: DfBase[ops.DfParentOp]
    locals: CompiledLocals = field(default_factory=dict)

    def __init__(
        self, builder: DfBase[DP], locals: CompiledLocals | None = None
    ) -> None:
        generic_builder = cast(DfBase[ops.DfParentOp], builder)
        if locals is None:
            locals = {}
        self.builder = generic_builder
        self.locals = locals

    def __getitem__(self, place: Place) -> Wire:
        """Constructs a wire for a local place in this DFG.

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
        child_types = [child.ty.to_hugr() for child in children]
        child_wires = [self[child] for child in children]
        wire = self.builder.add_op(ops.MakeTuple(child_types), *child_wires)[0]
        for child in children:
            if child.ty.linear:
                self.locals.pop(child.id)
        self.locals[place.id] = wire
        return wire

    def __setitem__(self, place: Place, port: Wire) -> None:
        # When assigning a struct value, we immediately unpack it recursively and only
        # store the leaf wires.
        is_return = isinstance(place, Variable) and is_return_var(place.name)
        if isinstance(place.ty, StructType) and not is_return:
            unpack = self.builder.add_op(
                ops.UnpackTuple([t.ty.to_hugr() for t in place.ty.fields]), port
            )
            for field, field_port in zip(place.ty.fields, unpack, strict=True):
                self[FieldAccess(place, field, None)] = field_port
            # If we had a previous wire assigned to this place, we need forget about it.
            # Otherwise, we might use this old value when looking up the place later
            self.locals.pop(place.id, None)
        else:
            self.locals[place.id] = port

    def __contains__(self, place: Place) -> bool:
        return place.id in self.locals

    def __copy__(self) -> "DFContainer":
        # Make a copy of the var map so that mutating the copy doesn't
        # mutate our variable mapping
        return DFContainer(self.builder, self.locals.copy())


class CompilerBase(ABC):
    """Base class for the Guppy compiler."""

    globals: CompiledContext

    def __init__(self, globals: CompiledContext) -> None:
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
