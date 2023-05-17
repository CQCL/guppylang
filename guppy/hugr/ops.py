import inspect
import sys
from typing import Annotated, Union, Optional, Any
from pydantic import Field

from .tys import Signature, TypeRow, ClassicType, SimpleType, ResourceSet
from .pydantic_extensions import BaseModel


# -----------------------------------------
# --------------- OpType ------------------
# -----------------------------------------

class Module(BaseModel, list=True, tagged=True):
    """ A module region node - parent will be the Root (or the node itself is the Root). """
    op: "ModuleOp"


class BasicBlock(BaseModel, list=True, tagged=True):
    """ A basic block in a control flow graph - parent will be a CFG node. """
    op: "BasicBlockOp"


class Case(BaseModel, list=True, tagged=True):
    """ A branch in a dataflow graph - parent will be a Conditional node. """
    op: "CaseOp"


class Dataflow(BaseModel, list=True, tagged=True):
    """ Nodes used inside dataflow containers (DFG, Conditional, TailLoop, def, BasicBlock). """
    op: "DataflowOp" = Field(tagged_union=True)


OpType = Union[Module, BasicBlock, Case, Dataflow]


# -------------------------------------------
# --------------- ModuleOp ------------------
# -------------------------------------------

class Root(BaseModel, list=True, tagged=True):
    """ The root of a module, parent of all other `ModuleOp`s. """
    pass


class Def(BaseModel, tagged=True):
    """ A function definition. Children nodes are the body of the definition. """
    signature: Signature


class Declare(BaseModel, tagged=True):
    """ External function declaration, linked at runtime. """
    signature: Signature


class NewType(BaseModel, tagged=True):
    """ Top level struct type definition. """
    name: str
    definition: SimpleType


class Const(BaseModel, list=True, tagged=True):
    """ A constant value definition. """
    value: "ConstValue"


ModuleOp = Union[Root, Def, Declare, NewType, Const]


# -----------------------------------------------
# --------------- BasicBlockOp ------------------
# -----------------------------------------------

class Block(BaseModel, tagged=True):
    """ A CFG basic block node. The signature is that of the internal Dataflow graph. """
    inputs: TypeRow
    outputs: TypeRow
    n_cases: int


class Exit(BaseModel, tagged=True):
    """ The single exit node of the CFG, has no children, stores the types of the CFG node output. """
    cfg_outputs: TypeRow


BasicBlockOp = Union[Block, Exit]


# -----------------------------------------
# --------------- CaseOp ------------------
# -----------------------------------------

class CaseOp(BaseModel):
    """ Case ops - nodes valid inside Conditional nodes. """
    signature: Signature  # The signature of the contained dataflow graph.


# ---------------------------------------------
# --------------- DataflowOp ------------------
# ---------------------------------------------

class Input(BaseModel, tagged=True):
    """ An input node. The outputs of this node are the inputs to the function. """
    types: TypeRow


class Output(BaseModel, tagged=True):
    """ An output node. The inputs are the outputs of the function. """
    types: TypeRow


class Call(BaseModel, tagged=True):
    """
    Call a function directly.

    The first port is connected to the def/declare of the function being
    called directly, with a `ConstE<Graph>` edge. The signature of the
    remaining ports matches the function being called.
    """
    signature: Signature


class CallIndirect(BaseModel, tagged=True):
    """ Call a function indirectly. Like call, but the first input is a standard dataflow graph type. """
    signature: Signature


class LoadConstant(BaseModel, tagged=True):
    """ Load a static constant in to the local dataflow graph. """
    datatype: ClassicType


class Leaf(BaseModel, tagged=True):
    """ Simple operation that has only value inputs+outputs and (potentially) StateOrder edges. """
    op: "LeafOp"


class DFG(BaseModel, tagged=True):
    """ A simply nested dataflow graph. """
    signature: Signature


class ControlFlow(BaseModel, tagged=True):
    """ Operation related to control flow. """
    op: "ControlFlowOp"


DataflowOp = Union[Input, Output, Call, CallIndirect, LoadConstant, Leaf, DFG, ControlFlow]


# ------------------------------------------------
# --------------- ControlFlowOp ------------------
# ------------------------------------------------

class Conditional(BaseModel, tagged=True):
    """ Conditional operation, defined by child `Case` nodes for each branch. """
    predicate_inputs: TypeRow  # The branch predicate. It's len is equal to the number of cases.
    inputs: TypeRow  # Other inputs passed to all cases.
    outputs: TypeRow  # Common output of all cases.


class TailLoop(BaseModel, tagged=True):
    """ Tail-controlled loop. """
    inputs: TypeRow
    outputs: TypeRow


class CFG(BaseModel, tagged=True):
    """ A dataflow node which is defined by a child CFG. """
    inputs: TypeRow
    outputs: TypeRow


ControlFlowOp = Union[Conditional, TailLoop, CFG]


# -----------------------------------------
# --------------- LeafOp ------------------
# -----------------------------------------

class CustomOp(BaseModel, list=True, tagged=True):
    """ A user-defined operation that can be downcasted by the extensions that define it. """
    op: "OpaqueOp"


class H(BaseModel, list=True, tagged=True):
    """ A Hadamard gate. """
    pass


class T(BaseModel, list=True, tagged=True):
    """ A T gate. """
    pass


class S(BaseModel, list=True, tagged=True):
    """ An S gate. """
    pass


class X(BaseModel, list=True, tagged=True):
    """ A Pauli X gate. """
    pass


class Y(BaseModel, list=True, tagged=True):
    """ A Pauli Y gate. """
    pass


class Z(BaseModel, list=True, tagged=True):
    """ A Pauli Z gate. """
    pass


class Tadj(BaseModel, list=True, tagged=True):
    """ An adjoint T gate. """
    pass


class Sadj(BaseModel, list=True, tagged=True):
    """ An adjoint S gate. """
    pass


class CX(BaseModel, list=True, tagged=True):
    """ A controlled X gate. """
    pass


class ZZMax(BaseModel, list=True, tagged=True):
    """ A maximally entangling ZZ phase gate. """
    pass


class Reset(BaseModel, list=True, tagged=True):
    """ A qubit reset operation. """
    pass


class Noop(BaseModel, list=True, tagged=True):
    """ A no-op operation. """
    ty: SimpleType


class Measure(BaseModel, list=True, tagged=True):
    """ A qubit measurement operation. """
    pass


class RzF64(BaseModel, list=True, tagged=True):
    """ A rotation of a qubit about the Pauli Z axis by an input float angle. """
    pass


class Copy(BaseModel, tagged=True):
    """ A copy operation for classical data. """
    # Note that a 0-ary copy acts as an explicit discard. Like any
    # stateful operation with no dataflow outputs, such a copy should
    # have a State output connecting it to the Output node.
    n_copies: int  # The number of copies to make.
    typ: ClassicType  # The type of the data to copy.


class Xor(BaseModel, list=True, tagged=True):
    """ A bitwise XOR operation. """
    pass


class MakeTuple(BaseModel, list=True, tagged=True):
    """ An operation that packs all its inputs into a tuple. """
    tys: TypeRow


class UnpackTuple(BaseModel, list=True, tagged=True):
    """ An operation that packs all its inputs into a tuple. """
    tys: TypeRow


class MakeNewType(BaseModel, tagged=True):
    """ An operation that wraps a value into a new type. """
    name: str  # The new type name.
    typ: SimpleType  # The wrapped type.


class Tag(BaseModel, list=True, tagged=True):
    """ An operation that creates a tagged sum value from one of its variants. """
    tag: int  # The variant to create.
    variants: TypeRow  # The variants of the sum type.


LeafOp = Union[CustomOp, H, S, T, X, Y, Z, Tadj, Sadj, CX, ZZMax, Reset, Noop,
               Measure, RzF64, Copy, Xor, MakeTuple, UnpackTuple, MakeNewType, Tag]


# -----------------------------------------
# --------------- OpaqueOp ----------------
# -----------------------------------------

class OpaqueOp(BaseModel):
    """ A wrapped CustomOp with fast equality checks. """
    id: str  # Operation name, cached for fast equality checks.
    op: "OpDef"  # The custom operation.


# --------------------------------------
# --------------- OpDef ----------------
# --------------------------------------

class OpDef(BaseModel):
    """ Serializable definition for dynamically loaded operations. """
    name: str  # Unique identifier of the operation.
    description: str  # Human readable description of the operation.
    inputs: list[tuple[Optional[str], SimpleType]]
    outputs: list[tuple[Optional[str], SimpleType]]
    misc: dict[str, Any] = {}  # Miscellaneous data associated with the operation.
    def_: Optional[str] = Field(alias="def")  # (YAML?)-encoded definition of the operation.
    resource_reqs: ResourceSet  # Resources required to execute this operation.


# -------------------------------------------
# --------------- ConstValue ----------------
# -------------------------------------------

class Int(BaseModel, list=True, tagged=True):
    """ An arbitrary length integer constant. """
    value: int


class Sum(BaseModel, tagged=True):
    """ An arbitrary length integer constant. """
    tag: int
    variants: TypeRow
    val: "ConstValue"


class Tuple(BaseModel, list=True, tagged=True):
    """ A tuple of constant values. """
    vals: list["ConstValue"]


class Opaque(BaseModel, list=True, tagged=True):
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
