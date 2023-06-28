import inspect
import sys
from typing import Literal, Union, Annotated
from pydantic import Field, BaseModel, root_validator, validator
from pydantic.utils import GetterDict


# ---------------------------------------------
# --------------- CustomType ------------------
# ---------------------------------------------


class CustomType(BaseModel):
    """An opaque type element. Contains an unique identifier and a reference to its
    definition."""

    id: str  # Unique identifier of the opaque type.
    params: "TypeRow"


# --------------------------------------------
# --------------- Container ------------------
# --------------------------------------------


def valid_linearity(ty: "SimpleType", stated_linearity: bool) -> None:
    if is_linear(ty) != stated_linearity:
        raise ValueError("Inner type linearity does not match outer.")


class Map(BaseModel):
    """Hash map from hashable key type to value type"""

    t: Literal["Map"] = "Map"
    k: "SimpleType"
    v: "SimpleType"
    l: bool

    @validator("k")
    def check_valid_key(cls, key: "SimpleType") -> "SimpleType":
        if not is_linear(key):
            raise ValueError("Key type cannot be linear.")
        return key

    @root_validator
    def check_value_linearity(cls, values: GetterDict) -> GetterDict:
        valid_linearity(values.get("v"), values.get("l"))
        return values


class MultiContainer(BaseModel):
    ty: "SimpleType"
    l: bool

    @root_validator
    def check_value_linearity(cls, values: GetterDict) -> GetterDict:
        valid_linearity(values.get("t"), values.get("l"))
        return values


class List(MultiContainer):
    """Variable sized list of types"""

    t: Literal["List"] = "List"


class Array(MultiContainer):
    """Known size array of"""

    t: Literal["Array"] = "Array"
    len: int


class AlgebraicContainer(BaseModel):
    row: "TypeRow"
    l: bool

    @root_validator
    def check_row_linearity(cls, values: GetterDict) -> GetterDict:
        row: TypeRow = values.get("row")
        l: bool = values.get("l")
        if any(is_linear(t) for t in row) != l:
            raise ValueError("A Sum/Tuple is non-linear if no elements are linear.")
        return values


class Tuple(AlgebraicContainer):
    """Product type, known-size tuple over elements of type row"""

    t: Literal["Tuple"] = "Tuple"


class Sum(AlgebraicContainer):
    """Sum type, variants are tagged by their position in the type row"""

    t: Literal["Sum"] = "Sum"


# ----------------------------------------------
# --------------- ClassicType ------------------
# ----------------------------------------------


class Variable(BaseModel):
    """A type variable identified by a name."""

    t: Literal["Var"] = "Var"
    name: str


class Int(BaseModel):
    """An arbitrary size integer."""

    t: Literal["I"] = "I"
    width: int


class F64(BaseModel):
    """A 64-bit floating point number."""

    t: Literal["F"] = "F"


class String(BaseModel):
    """An arbitrary length string."""

    t: Literal["S"] = "S"


class Graph(BaseModel):
    """A graph encoded as a value. It contains a concrete signature and a set of
    required resources."""

    t: Literal["G"] = "G"
    resources: "ResourceSet"
    signature: "Signature"


ResourceSet = list[str]  # TODO: Set not supported by MessagePack. Is list correct here?


class Opaque(BaseModel):
    """An opaque operation that can be downcasted by the extensions that define it."""

    t: Literal["Opaque"] = "Opaque"
    ty: CustomType
    linear: bool


# ----------------------------------------------
# --------------- LinearType -------------------
# ----------------------------------------------


class Qubit(BaseModel):
    """A qubit."""

    t: Literal["Q"] = "Q"


SimpleType = Annotated[
    Union[Qubit, Variable, Int, F64, String, Graph, List, Array, Map, Tuple, Sum],
    Field(discriminator="t"),
]


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
    """Describes the edges required to/from a node.

    This includes both the concept of "signature" in the spec, and also the target
    (value) of a call (constant).
    """

    input: TypeRow  # Value inputs of the function.
    output: TypeRow  # Value outputs of the function.
    const_input: TypeRow = Field(
        default_factory=list
    )  # Possible constE input (for call / load-constant).
    input_resources: ResourceSet = Field(default_factory=list)
    output_resources: ResourceSet = Field(default_factory=list)

    @classmethod
    def empty(cls) -> "Signature":
        return Signature(input=[], output=[], const_input=[])


# Now that all classes are defined, we need to update the ForwardRefs in all type
# annotations. We use some inspect magic to find all classes defined in this file.
classes = inspect.getmembers(
    sys.modules[__name__],
    lambda member: inspect.isclass(member) and member.__module__ == __name__,
)
for _, c in classes:
    if issubclass(c, BaseModel):
        c.update_forward_refs()
