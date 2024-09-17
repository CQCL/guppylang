"""Guppy standard module for dyadic rational angles."""

# mypy: disable-error-code="empty-body, misc, override"

import math
from typing import no_type_check

from hugr import val as hv
from hugr.std.float import FloatVal

# from hugr.std.float import FLOAT_T, FloatValue
from guppylang.decorator import guppy
from guppylang.module import GuppyModule

# from guppylang.prelude._internal.compiler.angle import guppy
# from guppylang.prelude._internal.compiler.quantum import ANGLE_EXTENSION, ANGLE_T

angles = GuppyModule("angles")


@guppy.struct(angles)
class angle:
    radians: float

    @guppy(angles)
    @no_type_check
    def __add__(self: "angle", other: "angle") -> "angle":
        return angle(self.radians + other.radians)

    @guppy(angles)
    @no_type_check
    def __sub__(self: "angle", other: "angle") -> "angle":
        return angle(self.radians - other.radians)

    @guppy
    @no_type_check
    def __mul__(self: "angle", other: int) -> "angle":
        return angle(self.radians * other)

    @guppy
    @no_type_check
    def __rmul__(self: "angle", other: int) -> "angle":
        return angle(self.radians * other)

    @guppy
    @no_type_check
    def __truediv__(self: "angle", other: int) -> "angle":
        return angle(self.radians / other)

    @guppy
    @no_type_check
    def __rtruediv__(self: "angle", other: int) -> "angle":
        return angle(other / self.radians)

    @guppy
    @no_type_check
    def __neg__(self: "angle") -> "angle":
        return angle(-self.radians)

    @guppy(angles)
    @no_type_check
    def __float__(self: "angle") -> float:
        return self.radians

    @guppy(angles)
    @no_type_check
    def __eq__(self: "angle", other: "angle") -> bool:
        return self.radians == other.radians


pi = guppy.constant(angles, "pi", ty="angle", value=hv.Tuple(FloatVal(math.pi)))
