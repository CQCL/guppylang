"""Guppy standard module for quantum operations."""

# mypy: disable-error-code="empty-body, misc"

from hugr import tys as ht

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude._internal.compiler import MeasureCompiler, QAllocCompiler
from guppylang.prelude._internal.quantum_ops import HSERIES_EXTENSION
from guppylang.prelude._internal.util import quantum_op, unsupported_op

quantum = GuppyModule("quantum")


@guppy.type(quantum, ht.Qubit, linear=True)
class qubit:
    @guppy.custom(quantum, QAllocCompiler())
    def __new__() -> "qubit": ...


@guppy.hugr_op(quantum, quantum_op("QAlloc"))
def dirty_qubit() -> qubit: ...


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


@guppy.hugr_op(quantum, quantum_op("ZZMax", ext=HSERIES_EXTENSION))
def zz_max(q1: qubit, q2: qubit) -> tuple[qubit, qubit]: ...


@guppy.hugr_op(quantum, quantum_op("Measure"))
def measure_return(q: qubit) -> tuple[qubit, bool]: ...


@guppy.hugr_op(
    quantum, quantum_op("Rz", ext=HSERIES_EXTENSION)
)  # TODO: Use the `tket.quantum` operation once we support angles
def rz(q: qubit, angle: float) -> qubit: ...


@guppy.hugr_op(
    quantum, unsupported_op("Rx")
)  # TODO: Use the `tket.quantum` operation once we support angles
def rx(q: qubit, angle: float) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("PhasedX", ext=HSERIES_EXTENSION))
def phased_x(q: qubit, angle1: float, angle2: float) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("ZZPhase", ext=HSERIES_EXTENSION))
def zz_phase(q1: qubit, q2: qubit, angle: float) -> tuple[qubit, qubit]: ...


@guppy.hugr_op(quantum, quantum_op("QFree"))
def discard(q: qubit) -> None: ...


@guppy.hugr_op(quantum, quantum_op("Reset"))
def reset(q: qubit) -> qubit: ...


@guppy.custom(quantum, MeasureCompiler())
def measure(q: qubit) -> bool: ...
