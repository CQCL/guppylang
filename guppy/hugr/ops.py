import inspect
import sys
from abc import ABC
from typing import Union, Optional, Any
from pydantic import Field

from .tys import Signature, TypeRow, ClassicType, SimpleType, ResourceSet, Graph, ContainerClassic, ContainerLinear
import guppy.hugr.tys as tys
from .pydantic_extensions import BaseModel


class BaseOp(ABC, BaseModel):
    """ Base class for ops that store their node's input/output types """
    def insert_port_types(self, in_types: TypeRow, out_types: TypeRow) -> None:
        """ Hook to insert type information from the input and output ports into the op """
        pass

    def insert_child_dfg_signature(self, inputs: TypeRow, outputs: TypeRow) -> None:
        """ Hook to insert type information from a child dataflow graph """
        pass

    def display_name(self) -> str:
        """ Name of the op for visualisation """
        return self.__class__.__name__


# -----------------------------------------
# --------------- OpType ------------------
# -----------------------------------------
class BasicBlock(BaseOp, list=True, tagged=True):
    """ A basic block in a control flow graph - parent will be a CFG node. """
    op: "BasicBlockOp"

    def insert_port_types(self, in_types: TypeRow, out_types: TypeRow) -> None:
        self.op.insert_port_types(in_types, out_types)

    def insert_child_dfg_signature(self, inputs: TypeRow, outputs: TypeRow) -> None:
        self.op.insert_child_dfg_signature(inputs, outputs)

    def display_name(self) -> str:
        return self.op.display_name()


class Case(BaseOp, list=True, tagged=True):
    """ A branch in a dataflow graph - parent will be a Conditional node. """
    op: "CaseOp"

    def insert_port_types(self, in_types: TypeRow, out_types: TypeRow) -> None:
        self.op.insert_port_types(in_types, out_types)

    def insert_child_dfg_signature(self, inputs: TypeRow, outputs: TypeRow) -> None:
        self.op.insert_child_dfg_signature(inputs, outputs)

    def display_name(self) -> str:
        return self.op.display_name()


class DummyOp(BaseOp, list=True, tagged=True):
    """ Nodes used inside dataflow containers (DFG, Conditional, TailLoop, def, BasicBlock). """
    name: str

    def display_name(self) -> str:
        return f'"{self.name}"'




# -------------------------------------------
# --------------- ModuleOp ------------------
# -------------------------------------------

class Module(BaseOp, list=True, tagged=True, newtype = True):
    """ The root of a module, parent of all other `ModuleOp`s. """

class Def(BaseOp, tagged=True):
    """ A function definition. Children nodes are the body of the definition.
    """
    name: str = "main"
    signature: Signature = Field(default_factory=Signature.empty)

    def insert_port_types(self, in_types: TypeRow, out_types: TypeRow) -> None:
        assert len(in_types) == 0
        assert len(out_types) == 1
        out = out_types[0]
        assert isinstance(out.ty, Graph)
        self.signature = out.ty.signature


class Declare(BaseOp, tagged=True):
    """ External function declaration, linked at runtime. """
    name: str = "main"
    signature: Signature = Field(default_factory=Signature.empty)

    def insert_port_types(self, in_types: TypeRow, out_types: TypeRow) -> None:
        assert len(in_types) == 0
        assert len(out_types) == 1
        out = out_types[0]
        assert isinstance(out.ty, Graph)
        self.signature = out.ty.signature


class NewType(BaseOp, tagged=True):
    """ Top level struct type definition. """
    name: str
    definition: SimpleType


class Const(BaseOp, list=True, tagged=True):
    """ A constant value definition. """
    value: "ConstValue"




# -----------------------------------------------
# --------------- BasicBlockOp ------------------
# -----------------------------------------------

class DFB(BaseOp, tagged=True):
    """ A CFG basic block node. The signature is that of the internal Dataflow graph. """
    inputs: TypeRow = Field(default_factory=list)
    other_outputs: TypeRow = Field(default_factory=list)
    predicate_variants: list[TypeRow] = Field(default_factory=list)

    def insert_port_types(self, in_types: TypeRow, out_types: TypeRow) -> None:
        # The types will be all None because it's not dataflow, but we only
        # care about the number of outputs. Note that we don't make use of
        # the HUGR feature where the variant data is appended to successor
        # input. Thus, `predicate_variants` will only contain empty rows.
        num_cases = len(out_types)
        self.predicate_variants = [[] for _ in range(num_cases)]

    def insert_child_dfg_signature(self, inputs: TypeRow, outputs: TypeRow) -> None:
        self.inputs = inputs
        self.other_outputs = outputs[1:]  # Skip branch predicate type


class Exit(BaseOp, tagged=True):
    """ The single exit node of the CFG, has no children, stores the types of the CFG node output. """
    cfg_outputs: TypeRow


BasicBlockOp = Union[DFB, Exit]


# -----------------------------------------
# --------------- CaseOp ------------------
# -----------------------------------------

class CaseOp(BaseOp):
    """ Case ops - nodes valid inside Conditional nodes. """
    signature: Signature = Field(default_factory=Signature.empty)  # The signature of the contained dataflow graph.

    def insert_child_dfg_signature(self, inputs: TypeRow, outputs: TypeRow) -> None:
        self.signature = tys.Signature(input=list(inputs), output=list(outputs))


# ---------------------------------------------
# --------------- DataflowOp ------------------
# ---------------------------------------------

class DataflowOp(BaseOp):
    pass
class Input(DataflowOp, tagged=True):
    """ An input node. The outputs of this node are the inputs to the function. """
    types: TypeRow = Field(default_factory=list)
    resources: "ResourceSet" = Field(default_factory=list)

    def insert_port_types(self, in_types: TypeRow, out_types: TypeRow) -> None:
        assert len(in_types) == 0
        self.types = list(out_types)


class Output(DataflowOp, tagged=True):
    """ An output node. The inputs are the outputs of the function. """
    types: TypeRow = Field(default_factory=list)
    resources: "ResourceSet"= Field(default_factory=list)

    def insert_port_types(self, in_types: TypeRow, out_types: TypeRow) -> None:
        assert len(out_types) == 0
        self.types = list(in_types)


class Call(DataflowOp, tagged=True):
    """
    Call a function directly.

    The first port is connected to the def/declare of the function being
    called directly, with a `ConstE<Graph>` edge. The signature of the
    remaining ports matches the function being called.
    """
    signature: Signature = Field(default_factory=Signature.empty)

    def insert_port_types(self, in_types: TypeRow, out_types: TypeRow) -> None:
        # The constE edge comes after the value inputs
        fun_ty = in_types[-1]
        assert isinstance(fun_ty.ty, Graph)
        self.signature = fun_ty.ty.signature


class CallIndirect(DataflowOp, tagged=True):
    """ Call a function indirectly. Like call, but the first input is a standard dataflow graph type. """
    signature: Signature = Field(default_factory=Signature.empty)
    
    def insert_port_types(self, in_types: TypeRow, out_types: TypeRow) -> None:
        fun_ty = in_types[0]
        assert isinstance(fun_ty, Graph)
        assert len(fun_ty.signature.input.types) == len(in_types) - 1
        assert len(fun_ty.signature.output.types) == len(out_types)
        self.signature = fun_ty.signature


class LoadConstant(DataflowOp, tagged=True):
    """ Load a static constant in to the local dataflow graph. """
    datatype: ClassicType


class LeafOp(DataflowOp, tagged=True, list=True):
    """ Simple operation that has only value inputs+outputs and (potentially) StateOrder edges. """
    op: "LeafOpUnion"

    def insert_port_types(self, in_types: TypeRow, out_types: TypeRow) -> None:
        self.op.insert_port_types(in_types, out_types)

    def insert_child_dfg_signature(self, inputs: TypeRow, outputs: TypeRow) -> None:
        self.op.insert_child_dfg_signature(inputs, outputs)

    def display_name(self) -> str:
        return self.op.display_name()


class DFG(DataflowOp, tagged=True):
    """ A simply nested dataflow graph. """
    signature: Signature = Field(default_factory=Signature.empty)

    def insert_child_dfg_signature(self, inputs: TypeRow, outputs: TypeRow) -> None:
        self.signature = Signature(input=list(inputs), output=list(outputs))


# ------------------------------------------------
# --------------- ControlFlowOp ------------------
# ------------------------------------------------

class Conditional(DataflowOp, list=True, tagged=True):
    """ Conditional operation, defined by child `Case` nodes for each branch. """
    predicate_inputs: list[TypeRow] = Field(default_factory=list)  # The possible rows of the predicate input
    other_inputs: TypeRow = Field(default_factory=list)  # Remaining input types
    outputs: TypeRow = Field(default_factory=list)  # Output types

    def insert_port_types(self, in_types: TypeRow, out_types: TypeRow) -> None:
        # First port is a predicate, i.e. a sum of tuple types. We need to unpack
        # those into a list of type rows
        pred = in_types[0]
        assert isinstance(pred.ty, ContainerClassic) or isinstance(pred.ty, ContainerLinear)
        assert isinstance(pred.ty.ty, tys.Sum)
        self.predicate_inputs = []
        for ty in pred.ty.ty.tys:
            assert isinstance(ty.ty, ContainerClassic) or isinstance(ty.ty, ContainerLinear)
            assert isinstance(ty.ty.ty, tys.Tuple)
            self.predicate_inputs.append(ty.ty.ty.tys)
        self.other_inputs = list(in_types[1:])
        self.outputs = list(out_types)


class TailLoop(DataflowOp, list=True, tagged=True):
    """ Tail-controlled loop. """
    just_inputs: TypeRow = Field(default_factory=list)  # Types that are only input
    just_outputs: TypeRow = Field(default_factory=list)  # Types that are only output
    rest: TypeRow = Field(default_factory=list)  # Types that are appended to both input and output

    def insert_port_types(self, in_types: TypeRow, out_types: TypeRow) -> None:
        assert in_types == out_types
        # self.just_inputs = list(in_types)
        # self.just_outputs = list(out_types)
        self.rest = list(in_types)


class CFG(DataflowOp, tagged=True):
    """ A dataflow node which is defined by a child CFG. """
    inputs: TypeRow = Field(default_factory=list)
    outputs: TypeRow = Field(default_factory=list)

    def insert_port_types(self, in_types: TypeRow, out_types: TypeRow) -> None:
        self.inputs = list(in_types)
        self.outputs = list(out_types)


ControlFlowOp = Union[Conditional, TailLoop, CFG]


# -----------------------------------------
# --------------- LeafOp ------------------
# -----------------------------------------

class CustomOp(BaseOp, list=True, tagged=True):
    """ A user-defined operation that can be downcasted by the extensions that define it. """
    op: "OpaqueOp"

    def display_name(self) -> str:
        return self.op.display_name()


class H(BaseOp, list=True, tagged=True):
    """ A Hadamard gate. """
    pass


class T(BaseOp, list=True, tagged=True):
    """ A T gate. """
    pass


class S(BaseOp, list=True, tagged=True):
    """ An S gate. """
    pass


class X(BaseOp, list=True, tagged=True):
    """ A Pauli X gate. """
    pass


class Y(BaseOp, list=True, tagged=True):
    """ A Pauli Y gate. """
    pass


class Z(BaseOp, list=True, tagged=True):
    """ A Pauli Z gate. """
    pass


class Tadj(BaseOp, list=True, tagged=True):
    """ An adjoint T gate. """
    pass


class Sadj(BaseOp, list=True, tagged=True):
    """ An adjoint S gate. """
    pass


class CX(BaseOp, list=True, tagged=True):
    """ A controlled X gate. """
    pass


class ZZMax(BaseOp, list=True, tagged=True):
    """ A maximally entangling ZZ phase gate. """
    pass


class Reset(BaseOp, list=True, tagged=True):
    """ A qubit reset operation. """
    pass


class Noop(BaseOp, list=True, tagged=True):
    """ A no-op operation. """
    ty: SimpleType

    def insert_port_types(self, in_types: TypeRow, out_types: TypeRow) -> None:
        assert len(in_types) == 1
        assert len(out_types) == 1
        assert in_types[0] == out_types[0]
        self.ty = in_types[0]


class Measure(BaseOp, list=True, tagged=True):
    """ A qubit measurement operation. """
    pass


class RzF64(BaseOp, list=True, tagged=True):
    """ A rotation of a qubit about the Pauli Z axis by an input float angle. """
    pass



class Xor(BaseOp, list=True, tagged=True):
    """ A bitwise XOR operation. """
    pass


class MakeTuple(BaseOp, list=True, tagged=True, newtype = True):
    """ An operation that packs all its inputs into a tuple. """
    tys: TypeRow = Field(default_factory=list)

    def insert_port_types(self, in_types: TypeRow, out_types: TypeRow) -> None:
        # If we have a single order edge as input, this is a unit
        if in_types == [None]:
            in_types = []
        self.tys = list(in_types)


class UnpackTuple(BaseOp, list=True, tagged=True):
    """ An operation that packs all its inputs into a tuple. """
    tys: TypeRow = Field(default_factory=list)

    def insert_port_types(self, in_types: TypeRow, out_types: TypeRow) -> None:
        self.tys = list(out_types)


class MakeNewType(BaseOp, tagged=True):
    """ An operation that wraps a value into a new type. """
    name: str  # The new type name.
    typ: SimpleType  # The wrapped type.


class Tag(BaseOp, list=True, tagged=True):
    """ An operation that creates a tagged sum value from one of its variants. """
    tag: int  # The variant to create.
    variants: TypeRow  # The variants of the sum type.


LeafOpUnion = Union[CustomOp, H, S, T, X, Y, Z, Tadj, Sadj, CX, ZZMax, Reset, Noop,
               Measure, RzF64, Xor, MakeTuple, UnpackTuple, MakeNewType, Tag]


OpType = Union[Module, 
               BasicBlock, Case, Module, Def, Declare, Const, DummyOp, BasicBlock, Conditional, TailLoop, CFG, Input, Output, Call, CallIndirect, LoadConstant, LeafOp, DFG]


# -----------------------------------------
# --------------- OpaqueOp ----------------
# -----------------------------------------

class OpaqueOp(BaseOp):
    """ A wrapped CustomOp with fast equality checks. """
    id: str  # Operation name, cached for fast equality checks.
    op: "OpDef"  # The custom operation.


# --------------------------------------
# --------------- OpDef ----------------
# --------------------------------------

class OpDef(BaseOp, allow_population_by_field_name=True):
    """ Serializable definition for dynamically loaded operations. """
    name: str  # Unique identifier of the operation.
    description: str  # Human readable description of the operation.
    inputs: list[tuple[Optional[str], SimpleType]]
    outputs: list[tuple[Optional[str], SimpleType]]
    misc: dict[str, Any]  # Miscellaneous data associated with the operation.
    def_: Optional[str] = Field(..., alias="def")  # (YAML?)-encoded definition of the operation.
    resource_reqs: ResourceSet  # Resources required to execute this operation.


# -------------------------------------------
# --------------- ConstValue ----------------
# -------------------------------------------

class Int(BaseOp, list=True, tagged=True):
    """ An arbitrary length integer constant. """
    value: int


class Sum(BaseOp, tagged=True):
    """ An arbitrary length integer constant. """
    tag: int
    variants: TypeRow
    val: "ConstValue"


class Tuple(BaseOp, list=True, tagged=True):
    """ A tuple of constant values. """
    vals: list["ConstValue"]


class Opaque(BaseOp, list=True, tagged=True):
    """ An opaque constant value. """
    ty: SimpleType
    val: "CustomConst"


CustomConst = Any  # TODO

ConstValue = Union[Int, Sum, Tuple, Opaque]


# Now that all classes are defined, we need to update the ForwardRefs
# in all type annotations. We use some inspect magic to find all classes
# defined in this file.
classes = inspect.getmembers(sys.modules[__name__],
                             lambda member: inspect.isclass(member) and member.__module__ == __name__)
for _, c in classes:
    if issubclass(c, BaseModel):
        c.update_forward_refs()
