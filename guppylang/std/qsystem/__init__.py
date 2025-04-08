from typing import no_type_check

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std import angles
from guppylang.std._internal.compiler.quantum import (
    QSYSTEM_EXTENSION,
    InoutMeasureCompiler,
)
from guppylang.std._internal.util import quantum_op
from guppylang.std.angles import angle
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit

qsystem = GuppyModule("qsystem")

qsystem.load(qubit)
qsystem.load_all(angles)


@guppy(qsystem)
@no_type_check
def phased_x(q: qubit, angle1: angle, angle2: angle) -> None:
    r"""phased_x gate command.

    .. math::

        \mathrm{phased\_x}(q, \theta_1, \theta_2)=
          \mathrm{Rz(\theta_2)Rx(\theta_1)Rz(\theta_2)}&=
          \begin{pmatrix}
          \cos(\frac{\pi \theta_1}{2}) &
            -i e^{-i \pi \theta_2}\sin(\frac{\pi\theta_1}{2})\\
          -i e^{i \pi \theta_2}\sin(\frac{\pi\theta_1}{2}) &
            \cos(\frac{\pi \theta_1}{2})
           \end{pmatrix}
    """
    f1 = float(angle1)
    f2 = float(angle2)
    _phased_x(q, f1, f2)


@guppy.hugr_op(quantum_op("ZZMax", ext=QSYSTEM_EXTENSION), module=qsystem)
@no_type_check
def zz_max(q1: qubit, q2: qubit) -> None:
    r"""zz_max gate command.

    .. math::
        \mathrm{zz\_max}(q_1,q_2)=\mathrm{zz\_max}(q_2,q_1)=
        \exp(\frac{- i \pi}{4}\big(Z \otimes Z \big))=
          \begin{pmatrix}
            e^{\frac{-i \pi}{4}} & 0 & 0 & 0 \\
            0 & e^{\frac{i \pi}{4}} & 0 & 0 \\
            0 & 0 & e^{\frac{i \pi}{4}} & 0 \\
            0 & 0 & 0 & e^{\frac{-i \pi}{4}}
        \end{pmatrix}
    """


@guppy(qsystem)
@no_type_check
def zz_phase(q1: qubit, q2: qubit, angle: angle) -> None:
    r"""zz_phase gate command.

    .. math::
        \mathrm{zz\_phase}(q_1,q_2,\theta)=\mathrm{zz\_phase}(q_2,q_1,\theta)=
        \exp(\frac{- i \pi \theta}{2}\big(Z \otimes Z \big))=
          \begin{pmatrix}
            e^{\frac{-i \pi \theta}{2}} & 0 & 0 & 0 \\
            0 & e^{\frac{i \pi \theta}{2}} & 0 & 0 \\
            0 & 0 & e^{\frac{i \pi \theta}{2}} & 0 \\
            0 & 0 & 0 & e^{\frac{-i \pi \theta}{2}}
        \end{pmatrix}
    """
    f = float(angle)
    _zz_phase(q1, q2, f)


@guppy(qsystem)
@no_type_check
def rz(q: qubit, angle: angle) -> None:
    r"""rz gate command.

    .. math::
        \mathrm{rz}(q,\theta)=
        \exp(\frac{- i \pi \theta}{2}\big(Z \big))=
          \begin{pmatrix}
            e^{\frac{-i \pi \theta}{2}} & 0  \\
            0 & e^{\frac{i \pi \theta}{2}}
        \end{pmatrix}
    """

    f1 = float(angle)
    _rz(q, f1)


@guppy.hugr_op(quantum_op("Measure", ext=QSYSTEM_EXTENSION), module=qsystem)
@no_type_check
def measure(q: qubit @ owned) -> bool:
    """Measure a qubit destructively."""


@guppy.custom(InoutMeasureCompiler("MeasureReset", QSYSTEM_EXTENSION), module=qsystem)
@no_type_check
def measure_and_reset(q: qubit) -> bool:
    """MeasureReset operation from the qsystem extension."""


@guppy.hugr_op(quantum_op("Reset", ext=QSYSTEM_EXTENSION), module=qsystem)
@no_type_check
def reset(q: qubit) -> None:
    """Reset a qubit to the |0> state."""


# TODO
# @guppy.hugr_op(quantum_op("TryQAlloc", ext=QSYSTEM_EXTENSION), module=qsystem)
# @no_type_check
# def _try_qalloc() -> Option[qubit]:
#     ..


@guppy.hugr_op(quantum_op("QFree", ext=QSYSTEM_EXTENSION), module=qsystem)
@no_type_check
def qfree(q: qubit @ owned) -> None: ...


# ------------------------------------------------------
# --------- Internal definitions -----------------------
# ------------------------------------------------------


@guppy.hugr_op(quantum_op("PhasedX", ext=QSYSTEM_EXTENSION), module=qsystem)
@no_type_check
def _phased_x(q: qubit, angle1: float, angle2: float) -> None:
    """PhasedX operation from the qsystem extension.

    See `guppylang.std.qsystem.phased_x` for a public definition that
    accepts angle parameters.
    """


@guppy.hugr_op(quantum_op("ZZPhase", ext=QSYSTEM_EXTENSION), module=qsystem)
@no_type_check
def _zz_phase(q1: qubit, q2: qubit, angle: float) -> None:
    """ZZPhase operation from the qsystem extension.

    See `guppylang.std.qsystem.zz_phase` for a public definition that
    accepts angle parameters.
    """


@guppy.hugr_op(quantum_op("Rz", ext=QSYSTEM_EXTENSION), module=qsystem)
@no_type_check
def _rz(q: qubit, angle: float) -> None:
    """Rz operation from the qsystem extension.

    See `guppylang.std.qsystem.rz` for a public definition that
    accepts angle parameters.
    """
