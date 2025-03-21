import itertools
from abc import ABC
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, cast

import tket2_exts
from hugr import Hugr, Node, Wire, ops
from hugr import tys as ht
from hugr.build import function as hf
from hugr.build.dfg import DP, DefinitionBuilder, DfBase
from hugr.hugr.base import OpVarCov
from hugr.hugr.node_port import ToNode
from hugr.std import PRELUDE

from guppylang.checker.core import FieldAccess, Globals, Place, PlaceId, Variable
from guppylang.definition.common import CheckedDef, CompilableDef, CompiledDef, DefId
from guppylang.definition.ty import TypeDef
from guppylang.definition.value import CompiledCallableDef
from guppylang.error import InternalGuppyError
from guppylang.tys.ty import StructType, Type

CompiledLocals = dict[PlaceId, Wire]


@dataclass(frozen=True)
class GlobalConstId:
    id: int
    base_name: str

    _fresh_ids = itertools.count()

    @staticmethod
    def fresh(base_name: str) -> "GlobalConstId":
        return GlobalConstId(next(GlobalConstId._fresh_ids), base_name)

    @property
    def name(self) -> str:
        return f"{self.base_name}.{self.id}"


class CompilerContext:
    """Compilation context containing all available definitions.

    Maintains a `worklist` of definitions which have been used by other compiled code
    (i.e. `compile_outer` has been called) but have not yet been compiled/lowered
    themselves (i.e. `compile_inner` has not yet been called).
    """

    module: DefinitionBuilder[ops.Module]
    checked: dict[DefId, CheckedDef]
    compiled: dict[DefId, CompiledDef]
    worklist: set[DefId]

    global_funcs: dict[GlobalConstId, hf.Function]

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
        self.global_funcs = {}
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
            with track_hugr_side_effects():
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

    def declare_global_func(
        self,
        const_id: GlobalConstId,
        func_ty: ht.PolyFuncType,
    ) -> tuple[hf.Function, bool]:
        """
        Creates a function builder for a global function if it doesn't already exist,
        else returns the existing one.
        """
        if const_id in self.global_funcs:
            return self.global_funcs[const_id], True
        func = self.module.define_function(
            name=const_id.name,
            input_types=func_ty.body.input,
            output_types=func_ty.body.output,
            type_params=func_ty.params,
        )
        self.global_funcs[const_id] = func
        return func, False


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

    ctx: CompilerContext

    def __init__(self, ctx: CompilerContext) -> None:
        self.ctx = ctx


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


QUANTUM_EXTENSION = tket2_exts.quantum()
RESULT_EXTENSION = tket2_exts.result()

#: List of extension ops that have side-effects, identified by their qualified name
EXTENSION_OPS_WITH_SIDE_EFFECTS: list[str] = [
    # Results should be order w.r.t. each other but also w.r.t. panics
    *(op_def.qualified_name() for op_def in RESULT_EXTENSION.operations.values()),
    PRELUDE.get_op("panic").qualified_name(),
    PRELUDE.get_op("exit").qualified_name(),
    # Qubit allocation and deallocation have the side-effect of changing the number of
    # available free qubits
    QUANTUM_EXTENSION.get_op("QAlloc").qualified_name(),
    QUANTUM_EXTENSION.get_op("QFree").qualified_name(),
    QUANTUM_EXTENSION.get_op("MeasureFree").qualified_name(),
]


def may_have_side_effect(op: ops.Op) -> bool:
    """Checks whether an operation could have a side-effect.

    We need to insert implicit state order edges between these kinds of nodes to ensure
    they are executed in the correct order, even if there is no data dependency.
    """
    match op:
        case ops.ExtOp() as ext_op:
            return ext_op.op_def().qualified_name() in EXTENSION_OPS_WITH_SIDE_EFFECTS
        case ops.Custom(op_name=op_name, extension=extension):
            qualified_name = f"{extension}.{op_name}" if extension else op_name
            return qualified_name in EXTENSION_OPS_WITH_SIDE_EFFECTS
        case ops.Call() | ops.CallIndirect():
            # Conservative choice is to assume that all calls could have side effects.
            # In the future we could inspect the call graph to figure out a more
            # precise answer
            return True
        case _:
            return False


@contextmanager
def track_hugr_side_effects() -> Iterator[None]:
    """Initialises the tracking of nodes with side-effects during Hugr building.

    Ensures that state-order edges are implicitly inserted between side-effectful nodes
    to ensure they are executed in the order they are added.
    """
    # Remember original `Hugr.add_node` method that is monkey-patched below.
    hugr_add_node = Hugr.add_node
    # Last node with potential side effects for each dataflow parent
    prev_node_with_side_effect: defaultdict[Node, Node | None] = defaultdict(
        lambda: None
    )

    def hugr_add_node_with_order(
        self: Hugr[OpVarCov],
        op: ops.Op,
        parent: ToNode | None = None,
        num_outs: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Node:
        """Monkey-patched version of `Hugr.add_node` that takes care of implicitly
        inserting state order edges between operations that could have side-effects.
        """
        new_node = hugr_add_node(self, op, parent, num_outs, metadata)
        if may_have_side_effect(op):
            handle_side_effect(new_node, self)
        return new_node

    def handle_side_effect(node: Node, hugr: Hugr[OpVarCov]) -> None:
        """Performs the actual order-edge insertion, assuming that `node` has a side-
        effect."""
        parent = hugr[node].parent
        if parent is not None:
            if prev := prev_node_with_side_effect[parent]:
                hugr.add_order_link(prev, node)
            else:
                # If this is the first side-effectful op in this DFG, make a recursive
                # call with the parent since the parent is also considered side-
                # effectful now. We shouldn't walk up through function definitions
                # or basic blocks though
                if not isinstance(hugr[parent].op, ops.FuncDefn | ops.DataflowBlock):
                    handle_side_effect(parent, hugr)
            prev_node_with_side_effect[parent] = node

    # Monkey-patch the `add_node` method
    Hugr.add_node = hugr_add_node_with_order  # type: ignore[method-assign]
    try:
        yield
    finally:
        Hugr.add_node = hugr_add_node  # type: ignore[method-assign]
