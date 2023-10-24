"""Guppy standard extension for quantum operations."""

# mypy: disable-error-code=empty-body

from guppy.hugr.tys import TypeBound
from guppy.prelude import builtin
from guppy.extension import GuppyExtension, OpCompiler
from guppy.hugr import ops, tys


class QuantumOpCompiler(OpCompiler):
    def __init__(self, op_name: str, ext: str = "quantum.tket2"):
        super().__init__(ops.CustomOp(extension=ext, op_name=op_name, args=[]))


_hugr_qubit = tys.Opaque(extension="prelude", id="qubit", args=[], bound=TypeBound.Any)


extension = GuppyExtension("quantum.tket2", dependencies=[builtin])


@extension.type(_hugr_qubit, linear=True)
class Qubit:
    pass


@extension.func(QuantumOpCompiler("H"))
def h(q: Qubit) -> Qubit:
    ...


@extension.func(QuantumOpCompiler("CX"))
def cx(control: Qubit, target: Qubit) -> tuple[Qubit, Qubit]:
    ...


@extension.func(QuantumOpCompiler("RzF64"))
def rz(q: Qubit, angle: float) -> Qubit:
    ...


@extension.func(QuantumOpCompiler("Measure"))
def measure(q: Qubit) -> tuple[Qubit, bool]:
    ...


@extension.func(QuantumOpCompiler("T"))
def t(q: Qubit) -> Qubit:
    ...


@extension.func(QuantumOpCompiler("Tdg"))
def tdg(q: Qubit) -> Qubit:
    ...


@extension.func(QuantumOpCompiler("Z"))
def z(q: Qubit) -> Qubit:
    ...


@extension.func(QuantumOpCompiler("X"))
def x(q: Qubit) -> Qubit:
    ...
