from typing import Annotated, Union, Optional
from pydantic import Field

from .pydantic_extensions import BaseModel


# ---------------------------------------------
# --------------- CustomType ------------------
# ---------------------------------------------

class CustomType(BaseModel):
    """ An opaque type element. Contains an unique identifier and a reference to its definition. """
    id: str  # Unique identifier of the opaque type.f
    params: "TypeRow"


# ---------------------------------------------
# --------------- SimpleType ------------------
# ---------------------------------------------

class Classic(BaseModel, list=True):
    """ A type containing classical data. Elements of this type can be copied. """
    ty: "ClassicType"


class Linear(BaseModel, list=True):
    """ A type containing linear data. Elements of this type must be used exactly once. """
    ty: "LinearType"


SimpleType = Annotated[Union[Classic, Linear], Field(tagged_union=True)]


# --------------------------------------------
# --------------- Container ------------------
# --------------------------------------------

class List(BaseModel, list=True):
    """ Variable sized list of types """
    ty: Union["ClassicType", "LinearType"]


class Map(BaseModel, list=True):
    """ Hash map from hashable key type to value type """
    key: "ClassicType"
    value: Union["ClassicType", "LinearType"]


class Tuple(BaseModel, list=True):
    """ Product type, known-size tuple over elements of type row """
    tys: "TypeRow"


class Sum(BaseModel, list=True):
    """ Sum type, variants are tagged by their position in the type row """
    tys: "TypeRow"


class Array(BaseModel, list=True):
    """ Known size array of """
    ty: Union["ClassicType", "LinearType"]
    size: int


class NewType(BaseModel, list=True):
    """ Named type defined by, but distinct from, ty. """
    name: str
    ty: Union["ClassicType", "LinearType"]


Container = Annotated[Union[List, Map, Tuple, Sum, Array, NewType], Field(tagged_union=True)]


# ----------------------------------------------
# --------------- ClassicType ------------------
# ----------------------------------------------

class Variable(BaseModel, list=True):
    """ A type variable identified by a name. """
    name: str


class Int(BaseModel, list=True):
    """ An arbitrary size integer. """
    size: int


class F64(BaseModel, list=True):
    """ A 64-bit floating point number. """
    pass


class String(BaseModel, list=True):
    """ An arbitrary length string. """
    pass


class Graph(BaseModel, list=True):
    """ A graph encoded as a value. It contains a concrete signature and a set of required resources. """
    resources: "ResourceSet"
    signature: "Signature"


ResourceSet = set[str]


class ContainerClassic(BaseModel, list=True, serialize_as="Container"):
    """ A nested definition containing other classic types. """
    ty: "Container"


class OpaqueClassic(BaseModel, list=True, serialize_as="Opaque"):
    """ An opaque operation that can be downcasted by the extensions that define it. """
    ty: CustomType


ClassicType = Annotated[Union[Variable, Int, F64, String, Graph, ContainerClassic, OpaqueClassic], Field(tagged_union=True)]


# ----------------------------------------------
# --------------- LinearType -------------------
# ----------------------------------------------

class Qubit(BaseModel, list=True):
    """ A qubit. """
    pass


class OpaqueLinear(BaseModel, list=True, serialize_as="Opaque"):
    """ A linear opaque operation that can be downcasted by the extensions that define it. """
    ty: CustomType


class ContainerLinear(BaseModel, list=True, serialize_as="Container"):
    """ A nested definition containing other linear types. """
    ty: Container


LinearType = Annotated[Union[Qubit, OpaqueLinear, ContainerLinear], Field(tagged_union=True)]


# -------------------------------------------
# --------------- TypeRow -------------------
# -------------------------------------------

class TypeRow(BaseModel):
    """ List of types, used for function signatures. """
    types: list[SimpleType]  # The datatypes in the row.


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
    const_input: Optional[ClassicType]  # Possible constE input (for call / load-constant).
