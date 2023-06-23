import inspect
import sys
from abc import ABC
from typing import Annotated, Literal, Union, Optional, Any
from pydantic import Field, BaseModel

from .tys import Signature, TypeRow,  SimpleType, ResourceSet, Graph
import guppy.hugr.tys as tys

NodeID = int

class BaseOp(ABC, BaseModel):
    """ Base class for ops that store their node's input/output types """
    # Parent node index of node the op belongs to, used only at serialization time
    parent: NodeID = 0
    def insert_port_types(self, in_types: TypeRow, out_types: TypeRow) -> None:
        """ Hook to insert type information from the input and output ports into the op """
        pass

    def insert_child_dfg_signature(self, inputs: TypeRow, outputs: TypeRow) -> None:
        """ Hook to insert type information from a child dataflow graph """
        pass

    def display_name(self) -> str:
        """ Name of the op for visualisation """
        return self.__class__.__name__


class DummyOp(BaseOp):
    """ Nodes used inside dataflow containers (DFG, Conditional, TailLoop, def,
    BasicBlock). """
    op: Literal["DummyOp"] = "DummyOp"
    name: str

    def display_name(self) -> str:
        return f'"{self.name}"'



# ----------------------------------------------------------
# --------------- Module level operations ------------------
# ----------------------------------------------------------

class Module(BaseOp):
    """ The root of a module, parent of all other `ModuleOp`s. """
    op: Literal["Module"] = "Module"


class Def(BaseOp):
    """ A function definition. Children nodes are the body of the definition.
    """
    op: Literal["Def"] = "Def"

    name: str = "main"
    signature: Signature = Field(default_factory=Signature.empty)

    def insert_port_types(self, in_types: TypeRow, out_types: TypeRow) -> None:
        assert len(in_types) == 0
        assert len(out_types) == 1
        out = out_types[0]
        assert isinstance(out, Graph)
        self.signature = out.signature


class Declare(BaseOp):
    """ External function declaration, linked at runtime. """
    op: Literal["Declare"] = "Declare"
    name: str = "main"
    signature: Signature = Field(default_factory=Signature.empty)

    def insert_port_types(self, in_types: TypeRow, out_types: TypeRow) -> None:
        assert len(in_types) == 0
        assert len(out_types) == 1
        out = out_types[0]
        assert isinstance(out, Graph)
        self.signature = out.signature

class Const(BaseOp):
    """ A constant value definition. """
    op: Literal["Const"] = "Const"
    value: "ConstValue"




# -----------------------------------------------
# --------------- BasicBlock types ------------------
# -----------------------------------------------


class BasicBlock(BaseOp):
    """ A basic block in a control flow graph - parent will be a CFG node. """
    op: Literal["BasicBlock"] = "BasicBlock"


class DFB(BasicBlock):
    """ A CFG basic block node. The signature is that of the internal Dataflow
    graph. """
    block: Literal["DFB"] = "DFB"
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


class Exit(BasicBlock):
    """ The single exit node of the CFG, has no children, stores the types of
    the CFG node output. """
    block: Literal["Exit"] = "Exit"
    cfg_outputs: TypeRow


BasicBlockOp = Annotated[Union[DFB, Exit], Field(discriminator="block")]


# ---------------------------------------------
# --------------- DataflowOp ------------------
# ---------------------------------------------

class DataflowOp(BaseOp):
    pass

class Input(DataflowOp):
    """ An input node. The outputs of this node are the inputs to the function. """
    op: Literal["Input"] = "Input"
    types: TypeRow = Field(default_factory=list)
    resources: "ResourceSet" = Field(default_factory=list)

    def insert_port_types(self, in_types: TypeRow, out_types: TypeRow) -> None:
        assert len(in_types) == 0
        self.types = list(out_types)


class Output(DataflowOp):
    """ An output node. The inputs are the outputs of the function. """
    op: Literal["Output"] = "Output"
    types: TypeRow = Field(default_factory=list)
    resources: "ResourceSet"= Field(default_factory=list)

    def insert_port_types(self, in_types: TypeRow, out_types: TypeRow) -> None:
        assert len(out_types) == 0
        self.types = list(in_types)


class Call(DataflowOp):
    """
    Call a function directly.

    The first port is connected to the def/declare of the function being
    called directly, with a `ConstE<Graph>` edge. The signature of the
    remaining ports matches the function being called.
    """
    op: Literal["Call"] = "Call"
    signature: Signature = Field(default_factory=Signature.empty)

    def insert_port_types(self, in_types: TypeRow, out_types: TypeRow) -> None:
        # The constE edge comes after the value inputs
        fun_ty = in_types[-1]
        assert isinstance(fun_ty, Graph)
        self.signature = fun_ty.signature


class CallIndirect(DataflowOp):
    """ Call a function indirectly. Like call, but the first input is a standard dataflow graph type. """
    op: Literal["CallIndirect"] = "CallIndirect"
    signature: Signature = Field(default_factory=Signature.empty)
    
    def insert_port_types(self, in_types: TypeRow, out_types: TypeRow) -> None:
        fun_ty = in_types[0]
        assert isinstance(fun_ty, Graph)
        assert len(fun_ty.signature.input) == len(in_types) - 1
        assert len(fun_ty.signature.output) == len(out_types)
        self.signature = fun_ty.signature


class LoadConstant(DataflowOp):
    """ Load a static constant in to the local dataflow graph. """
    op: Literal["LoadConstant"] = "LoadConstant"
    datatype: SimpleType


class LeafOp(DataflowOp):
    """ Simple operation that has only value inputs+outputs and (potentially) StateOrder edges. """
    op: Literal["LeafOp"] = "LeafOp"


class DFG(DataflowOp):
    """ A simply nested dataflow graph. """
    op: Literal["DFG"] = "DFG"
    signature: Signature = Field(default_factory=Signature.empty)

    def insert_child_dfg_signature(self, inputs: TypeRow, outputs: TypeRow) -> None:
        self.signature = Signature(input=list(inputs), output=list(outputs))


# ------------------------------------------------
# --------------- ControlFlowOp ------------------
# ------------------------------------------------

class Conditional(DataflowOp):
    """ Conditional operation, defined by child `Case` nodes for each branch. """
    op: Literal["Conditional"] = "Conditional"
    predicate_inputs: list[TypeRow] = Field(default_factory=list)  # The possible rows of the predicate input
    other_inputs: TypeRow = Field(default_factory=list)  # Remaining input types
    outputs: TypeRow = Field(default_factory=list)  # Output types

    def insert_port_types(self, in_types: TypeRow, out_types: TypeRow) -> None:
        # First port is a predicate, i.e. a sum of tuple types. We need to unpack
        # those into a list of type rows
        pred = in_types[0]
        assert isinstance(pred, tys.Sum)
        self.predicate_inputs = []
        for ty in pred.row:
            # assert isinstance(ty.ty, ContainerClassic) or isinstance(ty.ty, ContainerLinear)
            assert isinstance(ty, tys.Tuple)
            self.predicate_inputs.append(ty.row)
        self.other_inputs = list(in_types[1:])
        self.outputs = list(out_types)


class Case(BaseOp):
    """ Case ops - nodes valid inside Conditional nodes. """
    op: Literal["Case"] = "Case"
    signature: Signature = Field(default_factory=Signature.empty)  # The signature of the contained dataflow graph.

    def insert_child_dfg_signature(self, inputs: TypeRow, outputs: TypeRow) -> None:
        self.signature = tys.Signature(input=list(inputs), output=list(outputs))


class TailLoop(DataflowOp):
    """ Tail-controlled loop. """
    op: Literal["TailLoop"] = "TailLoop"
    just_inputs: TypeRow = Field(default_factory=list)  # Types that are only input
    just_outputs: TypeRow = Field(default_factory=list)  # Types that are only output
    rest: TypeRow = Field(default_factory=list)  # Types that are appended to both input and output

    def insert_port_types(self, in_types: TypeRow, out_types: TypeRow) -> None:
        assert in_types == out_types
        # self.just_inputs = list(in_types)
        # self.just_outputs = list(out_types)
        self.rest = list(in_types)


class CFG(DataflowOp):
    """ A dataflow node which is defined by a child CFG. """
    op: Literal["CFG"] = "CFG"
    inputs: TypeRow = Field(default_factory=list)
    outputs: TypeRow = Field(default_factory=list)

    def insert_port_types(self, in_types: TypeRow, out_types: TypeRow) -> None:
        self.inputs = list(in_types)
        self.outputs = list(out_types)


ControlFlowOp = Union[Conditional, TailLoop, CFG]


# -----------------------------------------
# --------------- LeafOp ------------------
# -----------------------------------------

class CustomOp(LeafOp):
    """ A user-defined operation that can be downcasted by the extensions that define it. """
    lop: Literal["CustomOp"] = "CustomOp"
    custom: "OpaqueOp"

    def display_name(self) -> str:
        return self.custom.display_name()


class H(LeafOp):
    """ A Hadamard gate. """
    lop: Literal["H"] = "H"
    pass


class T(LeafOp):
    """ A T gate. """
    lop: Literal["T"] = "T"
    pass


class S(LeafOp):
    """ An S gate. """
    lop: Literal["S"] = "S"
    pass


class X(LeafOp):
    """ A Pauli X gate. """
    lop: Literal["X"] = "X"
    pass


class Y(LeafOp):
    """ A Pauli Y gate. """
    lop: Literal["Y"] = "Y"
    pass


class Z(LeafOp):
    """ A Pauli Z gate. """
    lop: Literal["Z"] = "Z"
    pass


class Tadj(LeafOp):
    """ An adjoint T gate. """
    lop: Literal["Tadj"] = "Tadj"
    pass


class Sadj(LeafOp):
    """ An adjoint S gate. """
    lop: Literal["Sadj"] = "Sadj"
    pass


class CX(LeafOp):
    """ A controlled X gate. """
    lop: Literal["CX"] = "CX"
    pass


class ZZMax(LeafOp):
    """ A maximally entangling ZZ phase gate. """
    lop: Literal["ZZMax"] = "ZZMax"
    pass


class Reset(LeafOp):
    """ A qubit reset operation. """
    lop: Literal["Reset"] = "Reset"
    pass


class Noop(LeafOp):
    """ A no-op operation. """
    lop: Literal["Noop"] = "Noop"
    ty: SimpleType

    def insert_port_types(self, in_types: TypeRow, out_types: TypeRow) -> None:
        assert len(in_types) == 1
        assert len(out_types) == 1
        assert in_types[0] == out_types[0]
        self.ty = in_types[0]


class Measure(LeafOp):
    """ A qubit measurement operation. """
    lop: Literal["Measure"] = "Measure"
    pass


class RzF64(LeafOp):
    """ A rotation of a qubit about the Pauli Z axis by an input float angle. """
    lop: Literal["RzF64"] = "RzF64"
    pass



class Xor(LeafOp):
    """ A bitwise XOR operation. """
    lop: Literal["Xor"] = "Xor"
    pass


class MakeTuple(LeafOp):
    """ An operation that packs all its inputs into a tuple. """
    lop: Literal["MakeTuple"] = "MakeTuple"
    tys: TypeRow = Field(default_factory=list)

    def insert_port_types(self, in_types: TypeRow, out_types: TypeRow) -> None:
        # If we have a single order edge as input, this is a unit
        if in_types == [None]:
            in_types = []
        self.tys = list(in_types)


class UnpackTuple(LeafOp):
    """ An operation that packs all its inputs into a tuple. """
    lop: Literal["UnpackTuple"] = "UnpackTuple"
    tys: TypeRow = Field(default_factory=list)

    def insert_port_types(self, in_types: TypeRow, out_types: TypeRow) -> None:
        self.tys = list(out_types)


class MakeNewType(LeafOp):
    """ An operation that wraps a value into a new type. """
    lop: Literal["MakeNewType"] = "MakeNewType"
    name: str  # The new type name.
    typ: SimpleType  # The wrapped type.


class Tag(LeafOp):
    """ An operation that creates a tagged sum value from one of its variants. """
    lop: Literal["Tag"] = "Tag"
    tag: int  # The variant to create.
    variants: TypeRow  # The variants of the sum type.


LeafOpUnion = Annotated[Union[CustomOp, H, S, T, X, Y, Z, Tadj, Sadj, CX, ZZMax, Reset, Noop,
               Measure, RzF64, Xor, MakeTuple, UnpackTuple, MakeNewType, Tag], Field(discriminator="lop")]


OpType = Annotated[Union[Module, 
               BasicBlock, Case, Module, Def, Declare, Const, DummyOp, BasicBlockOp, Conditional, TailLoop, CFG, Input, Output, Call, CallIndirect, LoadConstant, LeafOpUnion, DFG], Field(discriminator="op")]


# -----------------------------------------
# --------------- OpaqueOp ----------------
# -----------------------------------------

class OpaqueOp(BaseOp):
    """ A wrapped CustomOp with fast equality checks. """
    # op: Literal["OpaqueOp"] = "OpaqueOp"
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

class Int(BaseOp):
    """ An arbitrary length integer constant. """
    op: Literal["Int"] = "Int"
    value: int


class Sum(BaseOp):
    """ An arbitrary length integer constant. """
    op: Literal["Sum"] = "Sum"
    tag: int
    variants: TypeRow
    val: "ConstValue"


class Tuple(BaseOp):
    """ A tuple of constant values. """
    op: Literal["Tuple"] = "Tuple"
    vals: list["ConstValue"]


class Opaque(BaseOp):
    """ An opaque constant value. """
    op: Literal["Opaque"] = "Opaque"
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
