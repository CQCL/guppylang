"""Constant value variants for the `Const` operation."""

import inspect
import sys
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field
from typing_extensions import TypeAliasType

from guppylang.hugr.tys import Type

CustomConst = Any  # TODO


class ExtensionConst(BaseModel):
    """An extension constant value, that can check it is of a given [CustomType]."""

    c: Literal["Extension"] = "Extension"
    e: tuple[CustomConst]


class FunctionConst(BaseModel):
    """A higher-order function value."""

    c: Literal["Function"] = "Function"
    hugr: Any  # TODO


class Tuple(BaseModel):
    """A tuple."""

    c: Literal["Tuple"] = "Tuple"
    vs: list["Const"]


class Sum(BaseModel):
    """A Sum variant

    For any Sum type where this value meets the type of the variant indicated by the tag
    """

    c: Literal["Sum"] = "Sum"
    tag: int
    values: list["Const"]
    typ: Type


Const = TypeAliasType(
    "Const",
    Annotated[
        ExtensionConst | FunctionConst | Tuple | Sum,
        Field(discriminator="c"),
    ],
)


# Now that all classes are defined, we need to update the ForwardRefs in all type
# annotations. We use some inspect magic to find all classes defined in this file.
classes = inspect.getmembers(
    sys.modules[__name__],
    lambda member: inspect.isclass(member) and member.__module__ == __name__,
)
for _, c in classes:
    if issubclass(c, BaseModel):
        c.model_rebuild()
