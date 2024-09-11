"""Guppy standard module for quantum operations."""

# mypy: disable-error-code="empty-body, misc"

from hugr import tys as ht

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude._internal.compiler.quantum import (
    MeasureCompiler,
    QAllocCompiler,
)
from guppylang.prelude._internal.util import quantum_op
from guppylang.prelude.builtins import owned

quantum = GuppyModule("quantum")


@guppy.type(quantum, ht.Qubit, linear=True)
class qubit:
    @guppy.custom(quantum, QAllocCompiler())
    def __new__() -> "qubit": ...


@guppy.hugr_op(quantum, quantum_op("QAlloc"))
def dirty_qubit() -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("Measure"))
def measure_return(q: qubit @ owned) -> tuple[qubit, bool]: ...


@guppy.hugr_op(quantum, quantum_op("QFree"))
def discard(q: qubit @ owned) -> None: ...


@guppy.custom(quantum, MeasureCompiler())
def measure(q: qubit @ owned) -> bool: ...
