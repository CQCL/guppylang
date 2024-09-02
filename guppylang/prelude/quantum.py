"""Guppy standard module for quantum operations."""

# mypy: disable-error-code="empty-body, misc"

from collections.abc import Callable

from hugr import ops
from hugr import tys as ht

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude._internal.compiler import MeasureCompiler, QAllocCompiler
from guppylang.tys.subst import Inst

quantum = GuppyModule("quantum")


def quantum_op(
    op_name: str,
) -> Callable[[ht.FunctionType, Inst], ops.DataflowOp]:
    """Utility method to create Hugr quantum ops.

    Args:
        op_name: The name of the quantum operation.

    Returns:
        A function that takes an instantiation of the type arguments and returns
        a concrete HUGR op.
    """

    def op(ty: ht.FunctionType, inst: Inst) -> ops.DataflowOp:
        return ops.Custom(
            op_name=op_name, extension="quantum.tket2", signature=ty, args=[]
        )

    return op


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


@guppy.hugr_op(quantum, quantum_op("QFree"))
def discard(q: qubit) -> None: ...


@guppy.hugr_op(quantum, quantum_op("Reset"))
def reset(q: qubit) -> qubit: ...


@guppy.custom(quantum, MeasureCompiler())
def measure(q: qubit) -> bool: ...
