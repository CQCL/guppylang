"""Guppy standard module for quantum operations."""

# mypy: disable-error-code=empty-body

from guppylang.decorator import guppy
from guppylang.hugr import ops, tys
from guppylang.hugr.tys import TypeBound
from guppylang.module import GuppyModule

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


@guppy.hugr_op(quantum, quantum_op("CX"))
def cx(control: Qubit, target: Qubit) -> tuple[Qubit, Qubit]:
    ...


@guppy.hugr_op(quantum, quantum_op("RzF64"))
def rz(q: Qubit, angle: float) -> Qubit:
    ...


@guppy.hugr_op(quantum, quantum_op("Measure"))
def measure(q: Qubit) -> tuple[Qubit, bool]:
    ...


@guppy.hugr_op(quantum, quantum_op("T"))
def t(q: Qubit) -> Qubit:
    ...


@guppy.hugr_op(quantum, quantum_op("Tdg"))
def tdg(q: Qubit) -> Qubit:
    ...


@guppy.hugr_op(quantum, quantum_op("Z"))
def z(q: Qubit) -> Qubit:
    ...


@guppy.hugr_op(quantum, quantum_op("X"))
def x(q: Qubit) -> Qubit:
    ...
