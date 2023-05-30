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


# ---------------------------------------------
# --------------- SimpleType ------------------
# ---------------------------------------------

class Classic(BaseModel, list=True, tagged=True):
    """ A type containing classical data. Elements of this type can be copied. """
    ty: "ClassicType"


class Linear(BaseModel, list=True, tagged=True):
    """ A type containing linear data. Elements of this type must be used exactly once. """
    ty: "LinearType"


SimpleType = Union[Classic, Linear]


# --------------------------------------------
# --------------- Container ------------------
# --------------------------------------------

class ListClassic(BaseModel, list=True, tagged=True, tag="List"):
    """ Variable sized list of types """
    ty: "ClassicType"


class ListLinear(BaseModel, list=True, tagged=True, tag="List"):
    """ Variable sized list of types """
    ty: "LinearType"


class MapClassic(BaseModel, list=True, tagged=True, tag="Map"):
    """ Hash map from hashable key type to value type """
    key: "ClassicType"
    value: "ClassicType"


class MapLinear(BaseModel, list=True, tagged=True, tag="Map"):
    """ Hash map from hashable key type to value type """
    key: "ClassicType"
    value: "LinearType"


class Tuple(BaseModel, list=True, tagged=True):
    """ Product type, known-size tuple over elements of type row """
    tys: "TypeRow"


class Sum(BaseModel, list=True, tagged=True):
    """ Sum type, variants are tagged by their position in the type row """
    tys: "TypeRow"


class ArrayClassic(BaseModel, list=True, tagged=True, tag="Array"):
    """ Known size array of """
    ty: "ClassicType"
    size: int


class ArrayLinear(BaseModel, list=True, tagged=True, tag="Array"):
    """ Known size array of """
    ty: "LinearType"
    size: int


class NewClassicType(BaseModel, list=True, tagged=True, tag="NewType"):
    """ Named type defined by, but distinct from, ty. """
    name: str
    ty: "ClassicType"


class NewLinearType(BaseModel, list=True, tagged=True, tag="NewType"):
    """ Named type defined by, but distinct from, ty. """
    name: str
    ty: "LinearType"


ContainerC = Union[ListClassic, MapClassic, Tuple, Sum, ArrayClassic, NewClassicType]
ContainerL = Union[ListLinear, MapLinear, Tuple, Sum, ArrayLinear, NewLinearType]


# ----------------------------------------------
# --------------- ClassicType ------------------
# ----------------------------------------------

class Variable(BaseModel, list=True, tagged=True):
    """ A type variable identified by a name. """
    name: str


class Int(BaseModel, list=True, tagged=True):
    """ An arbitrary size integer. """
    size: int


class F64(BaseModel, list=True, tagged=True):
    """ A 64-bit floating point number. """
    pass


class String(BaseModel, list=True, tagged=True):
    """ An arbitrary length string. """
    pass


class Graph(BaseModel, list=True, tagged=True):
    """ A graph encoded as a value. It contains a concrete signature and a set of required resources. """
    resources: "ResourceSet"
    signature: "Signature"


ResourceSet = list[str]  # TODO: Set not supported by MessagePack. Is list correct here?


class ContainerClassic(BaseModel, list=True, tagged=True, tag="Container"):
    """ A nested definition containing other classic types. """
    ty: ContainerC


class OpaqueClassic(BaseModel, list=True, tagged=True, tag="Opaque"):
    """ An opaque operation that can be downcasted by the extensions that define it. """
    ty: CustomType


ClassicType = Union[Variable, Int, F64, String, Graph, ContainerClassic, OpaqueClassic]


# ----------------------------------------------
# --------------- LinearType -------------------
# ----------------------------------------------

class Qubit(BaseModel, list=True, tagged=True):
    """ A qubit. """
    pass


class OpaqueLinear(BaseModel, list=True, tagged=True, tag="Opaque"):
    """ A linear opaque operation that can be downcasted by the extensions that define it. """
    ty: CustomType


class ContainerLinear(BaseModel, list=True, tagged=True, tag="Container"):
    """ A nested definition containing other linear types. """
    ty: ContainerL


LinearType = Union[Qubit, OpaqueLinear, ContainerLinear]


# -------------------------------------------
# --------------- TypeRow -------------------
# -------------------------------------------

class TypeRow(BaseModel):
    """ List of types, used for function signatures. """
    types: list[SimpleType]  # The datatypes in the row.

    @classmethod
    def empty(cls):
        return TypeRow(types=[])


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
    const_input: TypeRow = Field(default_factory=TypeRow.empty)  # Possible constE input (for call / load-constant).

    @classmethod
    def empty(cls):
        return Signature(input=TypeRow.empty(), output=TypeRow.empty(), const_input=TypeRow.empty())


# Now that all classes are defined, we need to update the ForwardRefs
# in all type annotations. We use some inspect magic to find all classes
# defined in this file.
classes = inspect.getmembers(sys.modules[__name__],
                             lambda member: inspect.isclass(member) and member.__module__ == __name__)
for _, c in classes:
    if issubclass(c, BaseModel):
        c.update_forward_refs()
