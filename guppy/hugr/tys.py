import inspect
import sys
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    Field,
    ValidationError,
    ValidationInfo,
    ValidatorFunctionWrapHandler,
    WrapValidator,
)
from pydantic_core import PydanticCustomError
from typing_extensions import TypeAliasType


def _json_custom_error_validator(
    value: Any, handler: ValidatorFunctionWrapHandler, _info: ValidationInfo
) -> Any:
    """Simplify the error message to avoid a gross error stemming
    from exhaustive checking of all union options.

    As suggested at
    https://docs.pydantic.dev/latest/concepts/types/#named-recursive-types


    Used to define named recursive alias types.
    """
    try:
        return handler(value)
    except ValidationError as err:
        raise PydanticCustomError(
            "invalid_json",
            "Input is not valid json",
        ) from err


ExtensionId = str
ExtensionSet = list[  # TODO: Set not supported by MessagePack. Is list correct here?
    ExtensionId
]


# --------------------------------------------
# --------------- TypeParam ------------------
# --------------------------------------------


class TypeTypeParam(BaseModel):
    tp: Literal["Type"] = "Type"
    b: "TypeBound"


class BoundedNatParam(BaseModel):
    tp: Literal["BoundedNat"] = "BoundedNat"
    bound: int | None


class OpaqueParam(BaseModel):
    tp: Literal["Opaque"] = "Opaque"
    ty: "Opaque"


class ListParam(BaseModel):
    tp: Literal["List"] = "List"
    param: "TypeParam"


class TupleParam(BaseModel):
    tp: Literal["Tuple"] = "Tuple"
    params: list["TypeParam"]


TypeParam = TypeAliasType(
    "TypeParam",
    Annotated[
        TypeTypeParam | BoundedNatParam | OpaqueParam | ListParam | TupleParam,
        Field(discriminator="tp"),
        WrapValidator(_json_custom_error_validator),
    ],
)


# ------------------------------------------
# --------------- TypeArg ------------------
# ------------------------------------------


class CustomTypeArg(BaseModel):
    typ: None  # TODO
    value: str


class TypeTypeArg(BaseModel):
    tya: Literal["Type"] = "Type"
    ty: "Type"


class BoundedNatArg(BaseModel):
    tya: Literal["BoundedNat"] = "BoundedNat"
    n: int


class OpaqueArg(BaseModel):
    tya: Literal["Opaque"] = "Opaque"
    arg: CustomTypeArg


class SequenceArg(BaseModel):
    tya: Literal["Sequence"] = "Sequence"
    args: list["TypeArg"]


class ExtensionsArg(BaseModel):
    tya: Literal["Extensions"] = "Extensions"
    es: ExtensionSet


TypeArg = TypeAliasType(
    "TypeArg",
    Annotated[
        TypeTypeArg | BoundedNatArg | OpaqueArg | SequenceArg | ExtensionsArg,
        Field(discriminator="tya"),
        WrapValidator(_json_custom_error_validator),
    ],
)


# --------------------------------------------
# --------------- Container ------------------
# --------------------------------------------


class MultiContainer(BaseModel):
    ty: "Type"


class Array(MultiContainer):
    """Known size array of"""

    t: Literal["Array"] = "Array"
    len: int


class TupleType(BaseModel):
    """Product type, known-size tuple over elements of type row"""

    t: Literal["Tuple"] = "Tuple"
    inner: "TypeRow"


class UnitSum(BaseModel):
    """Simple predicate where all variants are empty tuples"""

    t: Literal["Sum"] = "Sum"

    s: Literal["Unit"] = "Unit"
    size: int


class GeneralSum(BaseModel):
    """General sum type that explicitly stores the types of the variants"""

    t: Literal["Sum"] = "Sum"

    s: Literal["General"] = "General"
    row: "TypeRow"


Sum = Annotated[UnitSum | GeneralSum, Field(discriminator="s")]
# ----------------------------------------------
# --------------- ClassicType ------------------
# ----------------------------------------------


class Variable(BaseModel):
    """A type variable identified by a de Bruijn index."""

    t: Literal["V"] = "V"
    i: int
    b: "TypeBound"


class USize(BaseModel):
    """Unsigned integer size type."""

    t: Literal["I"] = "I"


class FunctionType(BaseModel):
    """A graph encoded as a value. It contains a concrete signature and a set of
    required resources."""

    input: "TypeRow"  # Value inputs of the function.
    output: "TypeRow"  # Value outputs of the function.
    # The extension requirements which are added by the operation
    extension_reqs: "ExtensionSet" = Field(default_factory=list)

    @classmethod
    def empty(cls) -> "FunctionType":
        return FunctionType(input=[], output=[], extension_reqs=[])


class PolyFuncType(BaseModel):
    """A graph encoded as a value. It contains a concrete signature and a set of
    required resources."""

    t: Literal["G"] = "G"

    # The declared type parameters, i.e., these must be instantiated with the same
    # number of TypeArgs before the function can be called. Note that within the body,
    # variable (DeBruijn) index 0 is element 0 of this array, i.e. the variables are
    # bound from right to left.
    params: list[TypeParam]

    # Template for the function. May contain variables up to length of `params`
    body: FunctionType

    @classmethod
    def empty(cls) -> "PolyFuncType":
        return PolyFuncType(params=[], body=FunctionType.empty())


class TypeBound(Enum):
    Eq = "E"
    Copyable = "C"
    Any = "A"

    @staticmethod
    def from_linear(linear: bool) -> "TypeBound":
        return TypeBound.Any if linear else TypeBound.Copyable


class Opaque(BaseModel):
    """An opaque operation that can be downcasted by the extensions that define it."""

    t: Literal["Opaque"] = "Opaque"
    extension: ExtensionId
    id: str  # Unique identifier of the opaque type.
    args: list[TypeArg]
    bound: TypeBound


# ----------------------------------------------
# --------------- LinearType -------------------
# ----------------------------------------------


class Qubit(BaseModel):
    """A qubit."""

    t: Literal["Q"] = "Q"


Type = TypeAliasType(
    "Type",
    Annotated[
        Qubit | Variable | USize | PolyFuncType | Array | TupleType | Sum | Opaque,
        Field(discriminator="t"),
        WrapValidator(_json_custom_error_validator),
    ],
)


# -------------------------------------------
# --------------- TypeRow -------------------
# -------------------------------------------

TypeRow = list[Type]


# -------------------------------------------
# --------------- Signature -----------------
# -------------------------------------------


class Signature(BaseModel):
    """Describes the edges required to/from a node.

    This includes both the concept of "signature" in the spec, and also the target
    (value) of a call (constant).
    """

    signature: "PolyFuncType"  # The underlying signature

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
        c.model_rebuild()
