"""Guppy standard module for quantum operations."""

# mypy: disable-error-code="empty-body, misc, valid-type"

from typing import no_type_check

from hugr import tys as ht

from guppylang.decorator import guppy
from guppylang.prelude._internal.compiler.quantum import (
    HSERIES_EXTENSION,
    MeasureReturnCompiler,
    RotationCompiler,
)
from guppylang.prelude._internal.util import quantum_op
from guppylang.prelude.angles import angle
from guppylang.prelude.builtins import owned


@guppy.type(ht.Qubit, linear=True)
class qubit:
    @guppy
    @no_type_check
    def __new__() -> "qubit":
        q = dirty_qubit()
        reset(q)
        return q

    @guppy
    @no_type_check
    def h(self: "qubit") -> None:
        h(self)

    @guppy
    @no_type_check
    def cz(self: "qubit", target: "qubit") -> None:
        cz(self, target)

    @guppy
    @no_type_check
    def cx(self: "qubit", target: "qubit") -> None:
        cx(self, target)

    @guppy
    @no_type_check
    def measure_reset(self: "qubit") -> bool:
        res = measure_return(self)
        if res:
            self.x()
        return res

    @guppy
    @no_type_check
    def discard(self: "qubit" @ owned) -> None:
        discard(self)

    @guppy
    @no_type_check
    def x(self: "qubit") -> None:
        x(self)

    @guppy
    @no_type_check
    def y(self: "qubit") -> None:
        y(self)

    @guppy
    @no_type_check
    def z(self: "qubit") -> None:
        z(self)

    @guppy
    @no_type_check
    def t(self: "qubit") -> None:
        t(self)

    @guppy
    @no_type_check
    def s(self: "qubit") -> None:
        s(self)

    @guppy
    @no_type_check
    def tdg(self: "qubit") -> None:
        tdg(self)

    @guppy
    @no_type_check
    def sdg(self: "qubit") -> None:
        sdg(self)

    @guppy
    @no_type_check
    def rz(self: "qubit", angle: angle) -> None:
        rz(self, angle)

    @guppy
    @no_type_check
    def rx(self: "qubit", angle: angle) -> None:
        rx(self, angle)

    @guppy
    @no_type_check
    def ry(self: "qubit", angle: angle) -> None:
        ry(self, angle)

    @guppy
    @no_type_check
    def crz(self: "qubit", target: "qubit", angle: angle) -> None:
        crz(self, target, angle)

    # TODO toffoli doesn't make much sense with two controls

    # @guppy
    # @no_type_check
    # def toffoli(self: "qubit", control2: "qubit", target: "qubit") -> None:
    #     toffoli(self, control2, target)

    @guppy
    @no_type_check
    def zz_max(self: "qubit", q2: "qubit") -> None:
        zz_max(self, q2)


@guppy.hugr_op(quantum_op("H"))
def h(q: qubit) -> None: ...


@guppy.hugr_op(quantum_op("CZ"))
def cz(control: qubit, target: qubit) -> None: ...


@guppy.hugr_op(quantum_op("CY"))
def cy(control: qubit, target: qubit) -> None: ...


@guppy.hugr_op(quantum_op("CX"))
def cx(control: qubit, target: qubit) -> None: ...


@guppy.hugr_op(quantum_op("T"))
def t(q: qubit) -> None: ...


@guppy.hugr_op(quantum_op("S"))
def s(q: qubit) -> None: ...


@guppy.hugr_op(quantum_op("X"))
def x(q: qubit) -> None: ...


@guppy.hugr_op(quantum_op("Y"))
def y(q: qubit) -> None: ...


@guppy.hugr_op(quantum_op("Z"))
def z(q: qubit) -> None: ...


@guppy.hugr_op(quantum_op("Tdg"))
def tdg(q: qubit) -> None: ...


@guppy.hugr_op(quantum_op("Sdg"))
def sdg(q: qubit) -> None: ...


@guppy.hugr_op(quantum_op("ZZMax", ext=HSERIES_EXTENSION))
def zz_max(q1: qubit, q2: qubit) -> None: ...


@guppy.custom(RotationCompiler("Rz"))
def rz(q: qubit, angle: angle) -> None: ...


@guppy.custom(RotationCompiler("Rx"))
def rx(q: qubit, angle: angle) -> None: ...


@guppy.custom(RotationCompiler("Ry"))
def ry(q: qubit, angle: angle) -> None: ...


@guppy.custom(RotationCompiler("CRz"))
def crz(control: qubit, target: qubit, angle: angle) -> None: ...


@guppy.hugr_op(quantum_op("Toffoli"))
def toffoli(control1: qubit, control2: qubit, target: qubit) -> None: ...


@guppy.hugr_op(quantum_op("QAlloc"))
def dirty_qubit() -> qubit: ...


@guppy.custom(MeasureReturnCompiler())
def measure_return(q: qubit) -> bool: ...


@guppy.hugr_op(quantum_op("QFree"))
def discard(q: qubit @ owned) -> None: ...


@guppy
@no_type_check
def measure(q: qubit @ owned) -> bool:
    res = measure_return(q)
    discard(q)
    return res


@guppy
@no_type_check
def phased_x(q: qubit, angle1: angle, angle2: angle) -> None:
    f1 = float(angle1)
    f2 = float(angle2)
    _phased_x(q, f1, f2)


@guppy
@no_type_check
def zz_phase(q1: qubit, q2: qubit, angle: angle) -> None:
    f = float(angle)
    _zz_phase(q1, q2, f)


@guppy.hugr_op(quantum_op("Reset"))
def reset(q: qubit) -> None: ...


# ------------------------------------------------------
# --------- Internal definitions -----------------------
# ------------------------------------------------------


@guppy.hugr_op(quantum_op("PhasedX", ext=HSERIES_EXTENSION))
def _phased_x(q: qubit, angle1: float, angle2: float) -> None:
    """PhasedX operation from the hseries extension.

    See `guppylang.prelude.quantum.phased_x` for a public definition that
    accepts angle parameters.
    """


@guppy.hugr_op(quantum_op("ZZPhase", ext=HSERIES_EXTENSION))
def _zz_phase(q1: qubit, q2: qubit, angle: float) -> None:
    """ZZPhase operation from the hseries extension.

    See `guppylang.prelude.quantum.phased_x` for a public definition that
    accepts angle parameters.
    """
