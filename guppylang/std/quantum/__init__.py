"""Guppy standard module for quantum operations."""

# mypy: disable-error-code="empty-body, misc, valid-type"

from typing import no_type_check

from hugr import tys as ht

from guppylang.decorator import guppy
from guppylang.std._internal.compiler.quantum import (
    InoutMeasureCompiler,
    RotationCompiler,
)
from guppylang.std._internal.util import quantum_op
from guppylang.std.angles import angle, pi
from guppylang.std.array import array
from guppylang.std.lang import owned
from guppylang.std.option import Option


@guppy.type(ht.Qubit, copyable=False, droppable=False)
class qubit:
    @guppy.hugr_op(quantum_op("QAlloc"))
    @no_type_check
    def __new__() -> "qubit": ...

    @guppy
    @no_type_check
    def measure(self: "qubit" @ owned) -> bool:
        return measure(self)

    @guppy
    @no_type_check
    def project_z(self: "qubit") -> bool:
        return project_z(self)

    @guppy
    @no_type_check
    def discard(self: "qubit" @ owned) -> None:
        discard(self)


@guppy.hugr_op(quantum_op("TryQAlloc"))
@no_type_check
def maybe_qubit() -> Option[qubit]:
    """Try to allocate a qubit, returning `some(qubit)`
    if allocation succeeds or `nothing` if it fails."""


@guppy.hugr_op(quantum_op("H"))
@no_type_check
def h(q: qubit) -> None:
    r"""Hadamard gate command

    .. math::
        \mathrm{H}(q)= \frac{1}{\sqrt{2}}
          \begin{pmatrix}
            1 & 1 \\
            1 & -1
          \end{pmatrix}
    """


@guppy.hugr_op(quantum_op("CZ"))
@no_type_check
def cz(control: qubit, target: qubit) -> None:
    r"""Controlled-Z gate command.

    .. math::
        \mathrm{cz}(q_1,q_2)=
          \begin{pmatrix}
            1 & 0 & 0 & 0 \\
            0 & 1 & 0 & 0 \\
            0 & 0 & 1 & 0 \\
            0 & 0 & 0 & -1
          \end{pmatrix}
    """


@guppy.hugr_op(quantum_op("CY"))
@no_type_check
def cy(control: qubit, target: qubit) -> None:
    r"""Controlled-Y gate command.

    .. math::
        \mathrm{cy}(q_1,q_2)=
          \begin{pmatrix}
            1 & 0 & 0 & 0 \\
            0 & 1 & 0 & 0 \\
            0 & 0 & 0 & -i \\
            0 & 0 & i & 0
          \end{pmatrix}
    """


@guppy.hugr_op(quantum_op("CX"))
@no_type_check
def cx(control: qubit, target: qubit) -> None:
    r"""Controlled-X gate command.

    .. math::
        \mathrm{cx}(q_1,q_2)=
          \begin{pmatrix}
            1 & 0 & 0 & 0 \\
            0 & 1 & 0 & 0 \\
            0 & 0 & 0 & 1 \\
            0 & 0 & 1 & 0
          \end{pmatrix}
    """


@guppy.hugr_op(quantum_op("T"))
@no_type_check
def t(q: qubit) -> None:
    r"""T gate.

    .. math::
        \mathrm{T}(q)=
          \begin{pmatrix}
            1 & 0 \\
            0 & e^{i \frac{\pi}{4}}
           \end{pmatrix}

    """


@guppy.hugr_op(quantum_op("S"))
@no_type_check
def s(q: qubit) -> None:
    r"""S gate.

    .. math::
        \mathrm{S}(q)=
          \begin{pmatrix}
            1 & 0 \\
            0 & e^{i \frac{\pi}{2}}
           \end{pmatrix}

    """


@guppy.hugr_op(quantum_op("X"))
@no_type_check
def x(q: qubit) -> None:
    r"""X gate.

    .. math::
        \mathrm{X}(q)=
          \begin{pmatrix}
            0 & 1 \\
            1 & 0
           \end{pmatrix}

    """


@guppy.hugr_op(quantum_op("Y"))
@no_type_check
def y(q: qubit) -> None:
    r"""Y gate.

    .. math::
        \mathrm{Y}(q)=
          \begin{pmatrix}
            0 & -i \\
            i & 0
           \end{pmatrix}

    """


@guppy.hugr_op(quantum_op("Z"))
@no_type_check
def z(q: qubit) -> None:
    r"""Z gate.

    .. math::
        \mathrm{Z}(q)=
          \begin{pmatrix}
            1 & 0 \\
            0 & -1
           \end{pmatrix}

    """


@guppy.hugr_op(quantum_op("Tdg"))
@no_type_check
def tdg(q: qubit) -> None:
    r"""Tdg gate.

    .. math::
        \mathrm{T}^\dagger(q)=
          \begin{pmatrix}
            1 & 0 \\
            0 & e^{-i \frac{\pi}{4}}
           \end{pmatrix}

    """


@guppy.hugr_op(quantum_op("Sdg"))
@no_type_check
def sdg(q: qubit) -> None:
    r"""Sdg gate.

    .. math::
        \mathrm{S}^\dagger(q)=
          \begin{pmatrix}
            1 & 0 \\
            0 & e^{-i \frac{\pi}{2}}
           \end{pmatrix}

    """


@guppy.custom(RotationCompiler("Rz"))
@no_type_check
def rz(q: qubit, angle: angle) -> None:
    r"""Rz gate.

    .. math::
        \mathrm{Rz}(q, \theta)=
          \begin{pmatrix}
            e^{-\frac{1}{2}i \pi \theta} & 0 \\
            0 & e^{\frac{1}{2}i \pi \theta}
           \end{pmatrix}

    """


@guppy.custom(RotationCompiler("Rx"))
@no_type_check
def rx(q: qubit, angle: angle) -> None:
    r"""Rx gate.

    .. math::
        \mathrm{Rx}(q, \theta)=
          \begin{pmatrix}
            \cos(\frac{\pi \theta}{2}) & -i\sin(\frac{\pi \theta}{2}) \\
            -i\sin(\frac{\pi \theta}{2}) & \cos(\frac{\pi \theta}{2})
           \end{pmatrix}

    """


@guppy.custom(RotationCompiler("Ry"))
@no_type_check
def ry(q: qubit, angle: angle) -> None:
    r"""Ry gate.

    .. math::
        \mathrm{Ry}(q, \theta)=
          \begin{pmatrix}
            \cos(\frac{\pi \theta}{2}) & \sin(\frac{\pi \theta}{2}) \\
            \sin(\frac{\pi \theta}{2}) & \cos(\frac{\pi \theta}{2})
           \end{pmatrix}

    """


@guppy.custom(RotationCompiler("CRz"))
@no_type_check
def crz(control: qubit, target: qubit, angle: angle) -> None:
    r"""crz gate command.

    .. math::
        \mathrm{crz}(q_1,q_2,\theta)=
          \begin{pmatrix}
            e^{\frac{-i \pi \theta}{2}} & 0 & 0 & 0 \\
            0 & e^{\frac{i \pi \theta}{2}} & 0 & 0 \\
            0 & 0 & e^{\frac{i \pi \theta}{2}} & 0 \\
            0 & 0 & 0 & e^{\frac{-i \pi \theta}{2}}
        \end{pmatrix}
    """


@guppy.hugr_op(quantum_op("Toffoli"))
@no_type_check
def toffoli(control1: qubit, control2: qubit, target: qubit) -> None: ...


@guppy.custom(InoutMeasureCompiler())
@no_type_check
def project_z(q: qubit) -> bool: ...


@guppy.hugr_op(quantum_op("QFree"))
@no_type_check
def discard(q: qubit @ owned) -> None: ...


@guppy.hugr_op(quantum_op("MeasureFree"))
@no_type_check
def measure(q: qubit @ owned) -> bool: ...


@guppy.hugr_op(quantum_op("Reset"))
@no_type_check
def reset(q: qubit) -> None: ...


N = guppy.nat_var("N")


@guppy
@no_type_check
def measure_array(qubits: array[qubit, N] @ owned) -> array[bool, N]:
    """Measure an array of qubits, returning an array of bools."""
    return array(measure(q) for q in qubits)


@guppy
@no_type_check
def discard_array(qubits: array[qubit, N] @ owned) -> None:
    """Discard an array of qubits."""
    for q in qubits:
        discard(q)


# -------NON-PRIMITIVE-------


@guppy
@no_type_check
def ch(control: qubit, target: qubit) -> None:
    # based on https://quantumcomputing.stackexchange.com/a/15737
    ry(target, -pi / 4)
    cz(control, target)
    ry(target, pi / 4)
