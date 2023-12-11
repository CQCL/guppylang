import inspect
import sys
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

CustomConst = Any  # TODO


class ExtensionVal(BaseModel):
    """An extension constant value, that can check it is of a given [CustomType]."""

    v: Literal["Extension"] = "Extension"
    c: tuple[CustomConst]


class FunctionVal(BaseModel):
    """A higher-order function value."""

    v: Literal["Function"] = "Function"
    hugr: Any  # TODO


class Tuple(BaseModel):
    """A tuple."""

    v: Literal["Tuple"] = "Tuple"
    vs: list["Value"]


class Sum(BaseModel):
    """A Sum variant

    For any Sum type where this value meets the type of the variant indicated by the tag
    """

    v: Literal["Sum"] = "Sum"
    tag: int
    value: "Value"


Value = Annotated[ExtensionVal | FunctionVal | Tuple | Sum, Field(discriminator="v")]


# Now that all classes are defined, we need to update the ForwardRefs in all type
# annotations. We use some inspect magic to find all classes defined in this file.
classes = inspect.getmembers(
    sys.modules[__name__],
    lambda member: inspect.isclass(member) and member.__module__ == __name__,
)
for _, c in classes:
    if issubclass(c, BaseModel):
        c.update_forward_refs()
