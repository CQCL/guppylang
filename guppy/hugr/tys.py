import inspect
import sys
from typing import Literal, Union, Annotated
from pydantic import Field, BaseModel


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

class Map(BaseModel):
    """ Hash map from hashable key type to value type """
    t: Literal['Map'] = "Map"
    k: "SimpleType"
    v: "SimpleType"
    l: bool

class List(BaseModel):
    """ Variable sized list of types """
    t: Literal['List'] = "List"
    ty: "SimpleType"
    l: bool


class Tuple(BaseModel):
    """ Product type, known-size tuple over elements of type row """
    t: Literal['Tuple'] = "Tuple"
    row: "TypeRow"
    l: bool

class Sum(BaseModel):
    """ Sum type, variants are tagged by their position in the type row """
    t: Literal['Sum'] = "Sum"
    row: "TypeRow"
    l: bool


class Array(BaseModel):
    """ Known size array of """
    t: Literal['Array'] = "Array"
    ty: "SimpleType"
    len: int
    l:bool 



# ----------------------------------------------
# --------------- ClassicType ------------------
# ----------------------------------------------

class Variable(BaseModel):
    """ A type variable identified by a name. """
    t: Literal['Var'] = "Var"
    name: str


class Int(BaseModel):
    """ An arbitrary size integer. """
    t: Literal['I'] = "I"
    width: int


class F64(BaseModel):
    """ A 64-bit floating point number. """
    t: Literal['F'] = "F"


class String(BaseModel):
    """ An arbitrary length string. """
    t: Literal['S'] = "S"


class Graph(BaseModel):
    """ A graph encoded as a value. It contains a concrete signature and a set of required resources. """
    t: Literal['G'] = "G"
    resources: "ResourceSet"
    signature: "Signature"


ResourceSet = list[str]  # TODO: Set not supported by MessagePack. Is list correct here?



class Opaque(BaseModel):
    """ An opaque operation that can be downcasted by the extensions that define it. """
    t: Literal['Opaque'] = "Opaque"
    ty: CustomType
    linear: bool




# ----------------------------------------------
# --------------- LinearType -------------------
# ----------------------------------------------

class Qubit(BaseModel):
    """ A qubit. """
    t: Literal['Q'] = "Q"
    



SimpleType = Annotated[Union[Qubit, Variable, Int, F64, String, Graph, List, Array, Map, Tuple, Sum], Field(discriminator="t")]

def is_linear(ty: SimpleType) -> bool:
    if isinstance(ty, Qubit):
        return True
    elif isinstance(ty, (List, Tuple, Sum, Array, Map, Opaque)):
        return ty.l
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
