"""Guppy standard module for quantum operations."""

# mypy: disable-error-code=empty-body

from guppy.decorator import guppy
from guppy.hugr import ops, tys
from guppy.hugr.tys import TypeBound
from guppy.module import GuppyModule
from guppy.prelude._internal import MeasureCompiler

quantum = GuppyModule("quantum")


def quantum_op(op_name: str) -> ops.OpType:
    """Utility method to create Hugr quantum ops."""
    return ops.CustomOp(extension="quantum.tket2", op_name=op_name, args=[])


@guppy.type(
    quantum,
    tys.Opaque(extension="prelude", id="qubit", args=[], bound=TypeBound.Any),
    linear=True,
)
class Qubit:
    pass


@guppy.hugr_op(quantum, quantum_op("H"))
def h(q: Qubit) -> Qubit:
    ...


@guppy.hugr_op(quantum, quantum_op("CZ"))
def cz(control: Qubit, target: Qubit) -> tuple[Qubit, Qubit]:
    ...


@guppy.hugr_op(quantum, quantum_op("CX"))
def cx(control: Qubit, target: Qubit) -> tuple[Qubit, Qubit]:
    ...


@guppy.hugr_op(quantum, quantum_op("T"))
def t(q: Qubit) -> Qubit:
    ...


@guppy.hugr_op(quantum, quantum_op("S"))
def s(q: Qubit) -> Qubit:
    ...


@guppy.hugr_op(quantum, quantum_op("X"))
def x(q: Qubit) -> Qubit:
    ...


@guppy.hugr_op(quantum, quantum_op("Y"))
def y(q: Qubit) -> Qubit:
    ...


@guppy.hugr_op(quantum, quantum_op("Z"))
def z(q: Qubit) -> Qubit:
    ...


@guppy.hugr_op(quantum, quantum_op("Tdg"))
def tdg(q: Qubit) -> Qubit:
    ...


@guppy.hugr_op(quantum, quantum_op("Sdg"))
def sdg(q: Qubit) -> Qubit:
    ...


@guppy.hugr_op(quantum, quantum_op("ZZMax"))
def zz_max(q: Qubit) -> Qubit:
    ...


@guppy.hugr_op(quantum, quantum_op("Measure"))
def measure_q(q: Qubit) -> tuple[Qubit, bool]:
    ...


@guppy.hugr_op(quantum, quantum_op("RzF64"))
def rz(q: Qubit, angle: float) -> Qubit:
    ...


@guppy.hugr_op(quantum, quantum_op("RxF64"))
def rx(q: Qubit, angle: float) -> Qubit:
    ...


@guppy.hugr_op(quantum, quantum_op("RzF64"))
def phased_x(q: Qubit, angle1: float, angle2: float) -> Qubit:
    ...


@guppy.hugr_op(quantum, quantum_op("RzF64"))
def zz_phase(q1: Qubit, q2: Qubit, angle: float) -> tuple[Qubit, Qubit]:
    ...


@guppy.hugr_op(quantum, quantum_op("RzF64"))
def tk1(q: Qubit, angle1: float, angle2: float, angle3: float) -> Qubit:
    ...


@guppy.hugr_op(quantum, quantum_op("QAlloc"), name="Qubit")
def _Qubit() -> Qubit:
    ...


@guppy.hugr_op(quantum, quantum_op("QFree"))
def discard(q: Qubit) -> None:
    ...


@guppy.hugr_op(quantum, quantum_op("Reset"))
def reset(q: Qubit) -> Qubit:
    ...


@guppy.custom(quantum, MeasureCompiler())
def measure(q: Qubit) -> bool:
    ...

