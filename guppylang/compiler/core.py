import itertools
from abc import ABC
from collections import defaultdict
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, cast, overload

import tket2_exts
from hugr import Hugr, Node, Wire, ops
from hugr import tys as ht
from hugr.build import function as hf
from hugr.build.dfg import DP, DefinitionBuilder, DfBase
from hugr.hugr.base import OpVarCov
from hugr.hugr.node_port import ToNode
from hugr.std import PRELUDE
from typing_extensions import assert_never

from guppylang.checker.core import FieldAccess, Globals, Place, PlaceId, Variable
from guppylang.definition.common import (
    CheckedDef,
    CompilableDef,
    CompiledDef,
    DefId,
    MonomorphizableDef,
)
from guppylang.definition.ty import TypeDef
from guppylang.definition.value import CompiledCallableDef
from guppylang.diagnostic import Error
from guppylang.engine import ENGINE
from guppylang.error import GuppyError, InternalGuppyError
from guppylang.tys.arg import ConstArg, TypeArg
from guppylang.tys.builtin import nat_type
from guppylang.tys.common import ToHugrContext
from guppylang.tys.const import BoundConstVar, ConstValue
from guppylang.tys.param import ConstParam, Parameter, TypeParam
from guppylang.tys.subst import Inst
from guppylang.tys.ty import BoundTypeVar, NumericType, StructType, Type

if TYPE_CHECKING:
    from guppylang.tys.arg import Argument

CompiledLocals = dict[PlaceId, Wire]

#: Partial instantiation of generic type parameters for monomorphization.
#:
#: When compiling polymorphic definitions to Hugr, some of their generic parameters will
#: need to be monomorphized (e.g. to support language features that cannot be encoded
#: in Hugr, see `requires_monomorphization` for details). However, other generic
#: parameters can be faithfully captured in Hugr. Thus, we want to perform a *partial*
#: monomorphization when compiling to Hugr.
#:
#: A `mono_args: PartiallyMonomorphizedArgs` represents such a partial monomorphization
#: of generic parameters as a sequence of `Argument | None`. Concretely,
#: `mono_args[i] == None` means that the argument with index `i` is left as a
#: polymorphic Hugr type parameter, i.e. it is not monomorphised by Guppy. Otherwise,
#: `mono_args[i]` specifies the monomorphic instantiation  for parameter `i`. For
#: example, a function with 3 generic parameters that should all be retained in Hugr
#: will have mono_args = `(None, None, None)`.
#:
#: Finally, note that this sequence is required to be a tuple to ensure hashability.
PartiallyMonomorphizedArgs = tuple["Argument | None", ...]


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


#: Unique identifier for a partially monomorphized definition.
#:
#: If the `DefId` corresponds to a `MonomorphizableDef`, then the second tuple entry
#: should hold the corresponding partial monomorphization. Otherwise, the second entry
#: should be `None`.
#:
#: Note the following subtlety: Functions are instances of `MonomorphizableDef`, even if
#: they aren't actually generic! This means that for non-generic function definitions we
#: will have an empty tuple `()` as `PartiallyMonomorphizedArgs`, but never `None`.
#: `None` only shows up for kinds of definitions that are never monomorphized (e.g.
#: definitions of constants).
MonoDefId = tuple[DefId, PartiallyMonomorphizedArgs | None]

#: Unique identifier for global Hugr constants and functions, the latter with optional
#: monomorphized type arguments
MonoGlobalConstId = tuple[GlobalConstId, PartiallyMonomorphizedArgs | None]


@dataclass(frozen=True)
class EntryMonomorphizeError(Error):
    title: ClassVar[str] = "Invalid entry point"
    span_label: ClassVar[str] = (
        "Function `{name}` is not a valid compilation entry point since the value of "
        "generic paramater `{param}` is not known"
    )
    name: str
    param: Parameter


class CompilerContext(ToHugrContext):
    """Compilation context containing all available definitions.

    Maintains a `worklist` of definitions which have been used by other compiled code
    (i.e. `compile_outer` has been called) but have not yet been compiled/lowered
    themselves (i.e. `compile_inner` has not yet been called).
    """

    module: DefinitionBuilder[ops.Module]

    #: The definitions compiled so far. For `MonomorphizableDef`s, their id can occur
    #: multiple times here with respectively different partial monomorphizations. See
    #: `MonoDefId` and `PartiallyMonomorphizedArgs` for details.
    compiled: dict[MonoDefId, CompiledDef]

    # use dict over set for deterministic iteration order
    worklist: dict[MonoDefId, None]

    global_funcs: dict[MonoGlobalConstId, hf.Function]

    #: Partial instantiation for some of the type parameters of the current function for
    #: the purpose of monomorphization
    current_mono_args: PartiallyMonomorphizedArgs | None

    checked_globals: Globals

    def __init__(
        self,
        module: DefinitionBuilder[ops.Module],
    ) -> None:
        self.module = module
        self.worklist = {}
        self.compiled = {}
        self.global_funcs = {}
        self.checked_globals = Globals(None)
        self.current_mono_args = None

    @contextmanager
    def set_monomorphized_args(
        self, mono_args: PartiallyMonomorphizedArgs | None
    ) -> Iterator[None]:
        """Context manager to set the partial monomorphization for the function that is
        compiled currently being compiled.
        """
        old = self.current_mono_args
        self.current_mono_args = mono_args
        yield
        self.current_mono_args = old

    @overload
    def build_compiled_def(
        self, def_id: DefId, type_args: Inst
    ) -> tuple[CompiledDef, Inst]: ...

    @overload
    def build_compiled_def(self, def_id: DefId, type_args: None) -> CompiledDef: ...

    def build_compiled_def(
        self, def_id: DefId, type_args: Inst | None
    ) -> CompiledDef | tuple[CompiledDef, Inst]:
        """Returns the compiled definitions corresponding to the given ID.

        Might mutate the current Hugr if this definition has never been compiled before.
        """
        # TODO: The check below is a hack to support nested function definitions. We
        #  forgot to insert frames for nested functions into the DEF_STORE, which would
        #  make the call to `ENGINE.get_checked` below fail. For now, let's just short-
        #  cut if the function doesn't take any generic params (as is the case for all
        #  nested functions).
        #  See https://github.com/CQCL/guppylang/issues/1032
        if (def_id, ()) in self.compiled:
            if type_args is None:
                return self.compiled[def_id, ()]
            assert type_args == []
            return self.compiled[def_id, ()], type_args

        compile_outer: Callable[[], CompiledDef]
        match ENGINE.get_checked(def_id):
            case MonomorphizableDef(params=params) as monomorphizable:
                assert type_args is not None
                mono_args, rest = partially_monomorphize_args(params, type_args, self)
                if (def_id, mono_args) not in self.compiled:
                    self.compiled[def_id, mono_args] = monomorphizable.monomorphize(
                        self.module, mono_args, self
                    )
                    self.worklist[def_id, mono_args] = None
                return (self.compiled[def_id, mono_args], rest)
            case CompilableDef() as compilable:
                compile_outer = lambda: compilable.compile_outer(self.module, self)  # noqa: E731
            case CompiledDef() as compiled_defn:
                compile_outer = lambda: compiled_defn  # noqa: E731
            case defn:
                compile_outer = assert_never(defn)
        if (def_id, None) not in self.compiled:
            self.compiled[def_id, None] = compile_outer()
            self.worklist[def_id, None] = None
        if type_args is None:
            return self.compiled[def_id, None]
        return self.compiled[def_id, None], type_args

    def compile(self, defn: CheckedDef) -> None:
        """Compiles the given definition and all of its dependencies into the current
        Hugr."""
        # Check and compile the entry point
        entry_mono_args: PartiallyMonomorphizedArgs | None = None
        entry_compiled: CompiledDef
        match ENGINE.get_checked(defn.id):
            case MonomorphizableDef(params=params) as defn:
                # Entry point is not allowed to require monomorphization
                for param in params:
                    if requires_monomorphization(param):
                        err = EntryMonomorphizeError(defn.defined_at, defn.name, param)
                        raise GuppyError(err)
                # Thus, the partial monomorphization for the entry point is always empty
                entry_mono_args = tuple(None for _ in params)
                entry_compiled = defn.monomorphize(self.module, entry_mono_args, self)
            case CompilableDef() as defn:
                entry_compiled = defn.compile_outer(self.module, self)
            case CompiledDef() as defn:
                entry_compiled = defn
            case defn:
                entry_compiled = assert_never(defn)

        self.compiled[defn.id, entry_mono_args] = entry_compiled
        self.worklist[defn.id, entry_mono_args] = None

        # Compile definition bodies
        while self.worklist:
            next_id, mono_args = self.worklist.popitem()[0]
            next_def = self.compiled[next_id, mono_args]
            with track_hugr_side_effects(), self.set_monomorphized_args(mono_args):
                next_def.compile_inner(self)

    def get_instance_func(
        self,
        ty: Type | TypeDef,
        name: str,
        type_args: Inst,
    ) -> tuple[CompiledCallableDef, Inst] | None:
        from guppylang.engine import ENGINE

        parsed_func = self.checked_globals.get_instance_func(ty, name)
        if parsed_func is None:
            return None
        checked_func = ENGINE.get_checked(parsed_func.id)
        (compiled_func, args) = self.build_compiled_def(checked_func.id, type_args)
        assert isinstance(compiled_func, CompiledCallableDef)
        return (compiled_func, args)

    def declare_global_func(
        self,
        const_id: GlobalConstId,
        func_ty: ht.PolyFuncType,
        mono_args: PartiallyMonomorphizedArgs | None = None,
    ) -> tuple[hf.Function, bool]:
        """
        Creates a function builder for a global function if it doesn't already exist,
        else returns the existing one.
        """
        if (const_id, mono_args) in self.global_funcs:
            return self.global_funcs[const_id, mono_args], True
        func = self.module.define_function(
            name=const_id.name,
            input_types=func_ty.body.input,
            output_types=func_ty.body.output,
            type_params=func_ty.params,
        )
        self.global_funcs[const_id, mono_args] = func
        return func, False

    def type_var_to_hugr(self, var: BoundTypeVar) -> ht.Type:
        """Compiles a bound Guppy type variable into a Hugr type.

        Takes care of performing partial monomorphization as specified in the current
        context.
        """
        if self.current_mono_args is None:
            # If we're not inside a monomorphized context, just return the Hugr
            # variable with the same de Bruijn index
            return ht.Variable(var.idx, var.hugr_bound)

        match self.current_mono_args[var.idx]:
            # Either we have a decided to monomorphize the corresponding parameter...
            case TypeArg(ty=ty):
                return ty.to_hugr(self)
            # ... or we're still want to be generic in Hugr
            case None:
                # But in that case we'll have to down-shift the de Bruijn index to
                # account for earlier params that have been monomorphized away
                hugr_idx = compile_variable_idx(var.idx, self.current_mono_args)
                return ht.Variable(hugr_idx, var.hugr_bound)
            case _:
                raise InternalGuppyError("Invalid monomorphization")

    def const_var_to_hugr(self, var: BoundConstVar) -> ht.TypeArg:
        """Compiles a bound Guppy constant variable into a Hugr type argument.

        Takes care of performing partial monomorphization as specified in the current
        context.
        """
        if var.ty != nat_type():
            raise InternalGuppyError(
                "Tried to convert non-nat const type argument to Hugr. This should "
                "have been erased."
            )
        param = ht.BoundedNatParam(upper_bound=None)

        if self.current_mono_args is None:
            # If we're not inside a monomorphized context, just return the Hugr
            # variable with the same de Bruijn index
            return ht.VariableArg(var.idx, param)

        match self.current_mono_args[var.idx]:
            # Either we have a decided to monomorphize the corresponding parameter...
            case ConstArg(const=ConstValue(value=int(v))):
                return ht.BoundedNatArg(n=v)
            # ... or we're still want to be generic in Hugr
            case None:
                # But in that case we'll have to down-shift the de Bruijn index to
                # account for earlier params that have been monomorphized away
                hugr_idx = compile_variable_idx(var.idx, self.current_mono_args)
                return ht.VariableArg(hugr_idx, param)
            case _:
                raise InternalGuppyError("Invalid monomorphization")


@dataclass
class DFContainer:
    """A dataflow graph under construction.

    This class is passed through the entire compilation pipeline and stores a builder
    for the dataflow child-graph currently being constructed as well as all live local
    variables. Note that the variable map is mutated in-place and always reflects the
    current compilation state.
    """

    builder: DfBase[ops.DfParentOp]
    ctx: CompilerContext
    locals: CompiledLocals = field(default_factory=dict)

    def __init__(
        self,
        builder: DfBase[DP],
        ctx: CompilerContext,
        locals: CompiledLocals | None = None,
    ) -> None:
        generic_builder = cast(DfBase[ops.DfParentOp], builder)
        if locals is None:
            locals = {}
        self.builder = generic_builder
        self.ctx = ctx
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
        child_types = [child.ty.to_hugr(self.ctx) for child in children]
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
                ops.UnpackTuple([t.ty.to_hugr(self.ctx) for t in place.ty.fields]), port
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
        return DFContainer(self.builder, self.ctx, self.locals.copy())


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


def requires_monomorphization(param: Parameter) -> bool:
    """Checks if a type parameter must be monomorphized before compiling to Hugr.

    This is required for some Guppy language features that cannot be encoded in Hugr
    yet. Currently, this only applies to non-nat const parameters.
    """
    match param:
        case TypeParam():
            return False
        case ConstParam(ty=ty):
            return ty != NumericType(NumericType.Kind.Nat)
        case x:
            return assert_never(x)


def partially_monomorphize_args(
    params: Sequence[Parameter],
    args: Inst,
    ctx: CompilerContext,
) -> tuple[PartiallyMonomorphizedArgs, Inst]:
    """
    Given an instantiation of all type parameters, extracts the ones that will need to
    be monomorphized.

    Also takes care of normalising bound variables w.r.t. the current monomorphization.
    """
    mono_args: list[Argument | None] = []
    rem_args = []
    for param, arg in zip(params, args, strict=True):
        if requires_monomorphization(param):
            # The constant could still refer to a bound variable, so we need to
            # instantiate it w.r.t. to the current monomorphization
            match arg:
                case ConstArg(const=BoundConstVar(idx=idx)):
                    assert ctx.current_mono_args is not None
                    inst = ctx.current_mono_args[idx]
                    assert inst is not None
                    mono_args.append(inst)
                case TypeArg():
                    # TODO: Once we also have type args that require monomorphization,
                    #  we'll need to downshift de Bruijn indices here as well
                    raise NotImplementedError
                case arg:
                    mono_args.append(arg)
        else:
            mono_args.append(None)
            rem_args.append(arg)
    return tuple(mono_args), rem_args


def compile_variable_idx(idx: int, mono_args: PartiallyMonomorphizedArgs) -> int:
    """Returns the Hugr index for a variable.

    Takes care of shifting down Guppy's indices to account for the current partial
    monomorphization. This avoids gaps in Hugr indices due to the fact that not all
    Guppy parameters are lowered to Hugr (some are monomorphized away).
    """
    assert mono_args[idx] is None, "Should not compile monomorphized index"
    return sum(1 for arg in mono_args[:idx] if arg is None)


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
