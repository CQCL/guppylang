"""Guppy standard module for quantum operations."""

# mypy: disable-error-code="empty-body, misc"

from guppylang.decorator import guppy
from guppylang.prelude._internal.compiler.quantum import HSERIES_EXTENSION
from guppylang.prelude._internal.util import quantum_op, unsupported_op
from guppylang.prelude.builtins import owned
from guppylang.prelude.quantum import quantum, qubit


@guppy.hugr_op(quantum, quantum_op("H"))
def h(q: qubit @ owned) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("CZ"))
def cz(control: qubit @ owned, target: qubit @ owned) -> tuple[qubit, qubit]: ...


@guppy.hugr_op(quantum, quantum_op("CX"))
def cx(control: qubit @ owned, target: qubit @ owned) -> tuple[qubit, qubit]: ...


@guppy.hugr_op(quantum, quantum_op("T"))
def t(q: qubit @ owned) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("S"))
def s(q: qubit @ owned) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("X"))
def x(q: qubit @ owned) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("Y"))
def y(q: qubit @ owned) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("Z"))
def z(q: qubit @ owned) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("Tdg"))
def tdg(q: qubit @ owned) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("Sdg"))
def sdg(q: qubit @ owned) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("ZZMax", ext=HSERIES_EXTENSION))
def zz_max(q1: qubit @ owned, q2: qubit @ owned) -> tuple[qubit, qubit]: ...


@guppy.hugr_op(
    quantum, quantum_op("Rz", ext=HSERIES_EXTENSION)
)  # TODO: Use the `tket.quantum` operation once we support angles
def rz(q: qubit @ owned, angle: float) -> qubit: ...


@guppy.hugr_op(
    quantum, unsupported_op("Rx")
)  # TODO: Use the `tket.quantum` operation once we support angles
def rx(q: qubit @ owned, angle: float) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("PhasedX", ext=HSERIES_EXTENSION))
def phased_x(q: qubit @ owned, angle1: float, angle2: float) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("ZZPhase", ext=HSERIES_EXTENSION))
def zz_phase(
    q1: qubit @ owned, q2: qubit @ owned, angle: float
) -> tuple[qubit, qubit]: ...


@guppy.hugr_op(quantum, quantum_op("Reset"))
def reset(q: qubit @ owned) -> qubit: ...
