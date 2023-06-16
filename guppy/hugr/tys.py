import inspect
import sys
from typing import Union
from pydantic import Field

from .pydantic_extensions import BaseModel


# ---------------------------------------------
# --------------- CustomType ------------------
# ---------------------------------------------

class CustomType(BaseModel):
    """ An opaque type element. Contains an unique identifier and a reference to its definition. """
    id: str  # Unique identifier of the opaque type.
    params: "TypeRow"


# --------------------------------------------
# --------------- Container ------------------
# --------------------------------------------

class Map(BaseModel, list=True, tagged=True, newtype=True):
    """ Hash map from hashable key type to value type """
    key: "SimpleType"
    value: "SimpleType"
    linear: bool

class List(BaseModel, list=True, tagged=True, newtype=True):
    """ Variable sized list of types """
    ty: "SimpleType"
    linear: bool


class Tuple(BaseModel, list=True, tagged=True, newtype=True):
    """ Product type, known-size tuple over elements of type row """
    tys: "TypeRow"
    linear: bool

class Sum(BaseModel, list=True, tagged=True, newtype=True):
    """ Sum type, variants are tagged by their position in the type row """
    tys: "TypeRow"
    linear: bool


class Array(BaseModel, list=True, tagged=True,newtype=True):
    """ Known size array of """
    ty: "SimpleType"
    size: int
    linear:bool 


Container = Union[List, Tuple, Sum, Array, Map]

# ----------------------------------------------
# --------------- ClassicType ------------------
# ----------------------------------------------

class Variable(BaseModel, list=True, tagged=True):
    """ A type variable identified by a name. """
    name: str


class Int(BaseModel, list=True, tagged=True, tag="I"):
    """ An arbitrary size integer. """
    size: int


class F64(BaseModel, list=True, tagged=True, tag="F"):
    """ A 64-bit floating point number. """
    pass


class String(BaseModel, list=True, tagged=True, tag="S"):
    """ An arbitrary length string. """
    pass


class Graph(BaseModel, list=True, tagged=True, tag="G"):
    """ A graph encoded as a value. It contains a concrete signature and a set of required resources. """
    resources: "ResourceSet"
    signature: "Signature"


ResourceSet = list[str]  # TODO: Set not supported by MessagePack. Is list correct here?



class Opaque(BaseModel, list=True, tagged=True, tag="Opaque"):
    """ An opaque operation that can be downcasted by the extensions that define it. """
    ty: CustomType
    linear: bool




# ----------------------------------------------
# --------------- LinearType -------------------
# ----------------------------------------------

class Qubit(BaseModel, list=True, tagged=True, tag="Q"):
    """ A qubit. """
    pass



SimpleType = Union[Qubit, Variable, Int, F64, String, Graph, List, Array, Map, Tuple, Sum]

def is_linear(ty: SimpleType) -> bool:
    if isinstance(ty, Qubit):
        return True
    elif isinstance(ty, Container) or isinstance(ty, Opaque):
        return ty.linear
    return False
    
# -------------------------------------------
# --------------- TypeRow -------------------
# -------------------------------------------

TypeRow = list[SimpleType]


# -------------------------------------------
# --------------- Signature -----------------
# -------------------------------------------

class Signature(BaseModel):
    """
    Describes the edges required to/from a node. This includes both the
    concept of "signature" in the spec, and also the target (value) of a
    call (constant).
    """
    input: TypeRow  # Value inputs of the function.
    output: TypeRow  # Value outputs of the function.
    const_input: TypeRow = Field(default_factory=list)  # Possible constE input (for call / load-constant).
    input_resources: ResourceSet = Field(default_factory=list)
    output_resources: ResourceSet= Field(default_factory=list)

    @classmethod
    def empty(cls) -> "Signature":
        return Signature(input=[], output=[], const_input=[])


# Now that all classes are defined, we need to update the ForwardRefs
# in all type annotations. We use some inspect magic to find all classes
# defined in this file.
classes = inspect.getmembers(sys.modules[__name__],
                             lambda member: inspect.isclass(member) and member.__module__ == __name__)
for _, c in classes:
    if issubclass(c, BaseModel):
        c.update_forward_refs()
