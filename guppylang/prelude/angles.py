"""Guppy standard module for dyadic rational angles."""

# mypy: disable-error-code="empty-body, misc, override"

from typing import no_type_check

from hugr import val as hv

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude._internal.checker import CoercingChecker
from guppylang.prelude._internal.compiler.angle import AngleOpCompiler
from guppylang.prelude._internal.compiler.quantum import ANGLE_T
from guppylang.prelude.builtins import nat

angles = GuppyModule("angles")




def _hugr_angle_value(numerator: int, log_denominator: int) -> hv.Value:
    custom_const = {
        "log_denominator": log_denominator,
        "value": numerator,
    }
    return hv.Extension(
        name="ConstAngle",
        typ=ANGLE_T,
        val=custom_const,
        extensions=["tket2.angle"],
    )


pi = guppy.constant(angles, "pi", ty="angle", value=_hugr_angle_value(1, 1))


@guppy.type(angles, ANGLE_T)
class angle:
    """The type of angles represented as dyadic rational multiples of 2π."""

    @guppy.custom(angles, AngleOpCompiler("afromrad"), CoercingChecker())
    def __new__(radians: float) -> "angle": ...

    @guppy.custom(angles, AngleOpCompiler("aadd"))
    def __add__(self: "angle", other: "angle") -> "angle": ...

    @guppy.custom(angles, AngleOpCompiler("asub"))
    def __sub__(self: "angle", other: "angle") -> "angle": ...

    @guppy.custom(angles, AngleOpCompiler("aneg"))
    def __neg__(self: "angle") -> "angle": ...

    @guppy.custom(angles, AngleOpCompiler("atorad"))
    def __float__(self: "angle") -> float: ...

    @guppy.custom(angles, AngleOpCompiler("aeq"))
    def __eq__(self: "angle", other: "angle") -> bool: ...

    @guppy(angles)
    @no_type_check
    def __mul__(self: "angle", other: int) -> "angle":
        if other < 0:
            return self._nat_mul(nat(other))
        else:
            return -self._nat_mul(nat(other))

    @guppy(angles)
    @no_type_check
    def __rmul__(self: "angle", other: int) -> "angle":
        return self * other

    @guppy(angles)
    @no_type_check
    def __truediv__(self: "angle", other: int) -> "angle":
        if other < 0:
            return self._nat_div(nat(other))
        else:
            return -self._nat_div(nat(other))

    @guppy.custom(angles, AngleOpCompiler("amul"))
    def _nat_mul(self: "angle", other: nat) -> "angle": ...

    @guppy.custom(angles, AngleOpCompiler("aneg"))
    def _nat_div(self: "angle", other: nat) -> "angle": ...

    @guppy.custom(angles, AngleOpCompiler("aparts"))
    def _parts(self: "angle") -> tuple[nat, nat]: ...

    @guppy(angles)
    @no_type_check
    def numerator(self: "angle") -> nat:
        numerator, _ = self._parts()
        return numerator

    @guppy(angles)
    @no_type_check
    def log_denominator(self: "angle") -> nat:
        _, log_denominator = self._parts()
        return log_denominator
