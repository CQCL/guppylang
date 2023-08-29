import inspect
import sys
from abc import ABC
from typing import Literal, Union, Annotated
from pydantic import Field, BaseModel


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


class MultiContainer(BaseModel):
    ty: "SimpleType"


class List(MultiContainer):
    """Variable sized list of types"""

    t: Literal["List"] = "List"


class Array(MultiContainer):
    """Known size array of"""

    t: Literal["Array"] = "Array"
    len: int


class Tuple(BaseModel):
    """Product type, known-size tuple over elements of type row"""

    t: Literal["Tuple"] = "Tuple"
    inner: "TypeRow"


class Sum(ABC, BaseModel):
    """Sum type, variants are tagged by their position in the type row"""

    t: Literal["Sum"] = "Sum"


class SimpleSum(Sum):
    """Simple predicate where all variants are empty tuples"""

    s: Literal["Simple"] = "Simple"
    size: int


class GeneralSum(Sum):
    """General sum type that explicitly stores the types of the variants"""

    s: Literal["General"] = "General"
    row: "TypeRow"


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


class FunctionType(BaseModel):
    """A graph encoded as a value. It contains a concrete signature and a set of
    required resources."""

    t: Literal["G"] = "G"
    input: "TypeRow"  # Value inputs of the function.
    output: "TypeRow"  # Value outputs of the function.
    # The extension requirements which are added by the operation
    extension_reqs: "ExtensionSet"

    @classmethod
    def empty(cls) -> "FunctionType":
        return FunctionType(input=[], output=[], extension_reqs=[])


ExtensionId = str
ExtensionSet = list[
    ExtensionId
]  # TODO: Set not supported by MessagePack. Is list correct here?


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
    Union[Qubit, Variable, Int, F64, String, FunctionType, List, Array, Tuple, Sum],
    Field(discriminator="t"),
]


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

    signature: "FunctionType"  # The underlying signature

    # The extensions which are associated with all the inputs and carried through
    input_extensions: ExtensionSet


# Now that all classes are defined, we need to update the ForwardRefs in all type
# annotations. We use some inspect magic to find all classes defined in this file.
classes = inspect.getmembers(
    sys.modules[__name__],
    lambda member: inspect.isclass(member) and member.__module__ == __name__,
)
for _, c in classes:
    if issubclass(c, BaseModel):
        c.update_forward_refs()
