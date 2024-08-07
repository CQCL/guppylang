"""Guppy standard module for quantum operations."""

# mypy: disable-error-code="empty-body, misc"

import hugr
from hugr import ops
from hugr import tys as ht

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude._internal.compiler import MeasureCompiler, QAllocCompiler

quantum = GuppyModule("quantum")


def quantum_op(
    op_name: str,
    qubits: int = 1,
    in_bits: int = 0,
    out_bits: int = 0,
    out_qubits: int | None = None,
    in_floats: int = 0,
) -> ops.Custom:
    """Utility method to create Hugr quantum ops.

    Args:
        op_name: The name of the quantum operation.
        qubits: The number of qubits the operation acts on.
        in_bits: The number of input bits.
        out_bits: The number of output bits.
        out_qubits: The number of output qubits. If `None`, defaults to `qubits`.
    """
    # TODO: Use a common definition from either `hugr` or `tket2`, and drop all
    # the extra parameters.

    input = (
        [ht.Qubit for _ in range(qubits)]
        + [ht.Bool() for _ in range(in_bits)]
        + [hugr.std.float.FLOAT_T for _ in range(in_floats)]
    )

    out_qubits = out_qubits if out_qubits is not None else qubits
    output = [ht.Qubit for _ in range(out_qubits)] + [ht.Bool for _ in range(out_bits)]

    return ops.Custom(
        name=op_name,
        extension="quantum.tket2",
        signature=ht.FunctionType(input=input, output=output),
        args=[],
    )


@guppy.type(quantum, ht.Qubit, linear=True)
class qubit:
    @guppy.custom(quantum, QAllocCompiler())
    def __new__() -> "qubit": ...


@guppy.hugr_op(quantum, quantum_op("QAlloc", qubits=0, out_qubits=1))
def dirty_qubit() -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("H"))
def h(q: qubit) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("CZ", qubits=2))
def cz(control: qubit, target: qubit) -> tuple[qubit, qubit]: ...


@guppy.hugr_op(quantum, quantum_op("CX", qubits=2))
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


@guppy.hugr_op(quantum, quantum_op("ZZMax", qubits=2))
def zz_max(q1: qubit, q2: qubit) -> tuple[qubit, qubit]: ...


@guppy.hugr_op(quantum, quantum_op("Measure", out_bits=1))
def measure_return(q: qubit) -> tuple[qubit, bool]: ...


@guppy.hugr_op(quantum, quantum_op("RzF64", in_floats=1))
def rz(q: qubit, angle: float) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("RxF64", in_floats=1))
def rx(q: qubit, angle: float) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("PhasedX", in_floats=2))
def phased_x(q: qubit, angle1: float, angle2: float) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("ZZPhase", qubits=2, in_floats=1))
def zz_phase(q1: qubit, q2: qubit, angle: float) -> tuple[qubit, qubit]: ...


@guppy.hugr_op(quantum, quantum_op("TK1", in_floats=3))
def tk1(q: qubit, angle1: float, angle2: float, angle3: float) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("QFree", qubits=1, out_qubits=0))
def discard(q: qubit) -> None: ...


@guppy.hugr_op(quantum, quantum_op("Reset"))
def reset(q: qubit) -> qubit: ...


@guppy.custom(quantum, MeasureCompiler())
def measure(q: qubit) -> bool: ...
