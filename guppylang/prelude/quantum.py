"""Guppy standard module for quantum operations."""

# mypy: disable-error-code=empty-body

from guppylang.decorator import guppy
from guppylang.hugr import ops, tys
from guppylang.hugr.tys import TypeBound
from guppylang.module import GuppyModule
from guppylang.prelude._internal import MeasureCompiler

quantum = GuppyModule("quantum")


def quantum_op(op_name: str) -> ops.OpType:
    """Utility method to create Hugr quantum ops."""
    return ops.CustomOp(extension="quantum.tket2", op_name=op_name, args=[])


@guppy.type(
    quantum,
    tys.Opaque(extension="prelude", id="qubit", args=[], bound=TypeBound.Any),
    linear=True,
)
class qubit:
    pass


@guppy.hugr_op(quantum, quantum_op("H"))
def h(q: qubit) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("CZ"))
def cz(control: qubit, target: qubit) -> tuple[qubit, qubit]: ...


@guppy.hugr_op(quantum, quantum_op("CX"))
def cx(control: qubit, target: qubit) -> tuple[qubit, qubit]: ...


@guppy.hugr_op(quantum, quantum_op("T"))
def t(q: qubit) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("S"))
def s(q: qubit) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("X"))
def x(q: qubit) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("Y"))
def y(q: qubit) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("Z"))
def z(q: qubit) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("Tdg"))
def tdg(q: qubit) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("Sdg"))
def sdg(q: qubit) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("ZZMax"))
def zz_max(q1: qubit, q2: qubit) -> tuple[qubit, qubit]: ...


@guppy.hugr_op(quantum, quantum_op("Measure"))
def measure_return(q: qubit) -> tuple[qubit, bool]: ...


@guppy.hugr_op(quantum, quantum_op("RzF64"))
def rz(q: qubit, angle: float) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("RxF64"))
def rx(q: qubit, angle: float) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("PhasedX"))
def phased_x(q: qubit, angle1: float, angle2: float) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("ZZPhase"))
def zz_phase(q1: qubit, q2: qubit, angle: float) -> tuple[qubit, qubit]: ...


@guppy.hugr_op(quantum, quantum_op("TK1"))
def tk1(q: qubit, angle1: float, angle2: float, angle3: float) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("QAlloc"), name="qubit")
def _qubit() -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("QFree"))
def discard(q: qubit) -> None: ...


@guppy.hugr_op(quantum, quantum_op("Reset"))
def reset(q: qubit) -> qubit: ...


@guppy.custom(quantum, MeasureCompiler())
def measure(q: qubit) -> bool: ...
