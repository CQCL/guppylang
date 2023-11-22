"""Guppy standard module for quantum operations."""

# mypy: disable-error-code=empty-body

from guppy.decorator import guppy
from guppy.hugr import tys
from guppy.hugr.tys import TypeBound
from guppy.module import GuppyModule


quantum = GuppyModule("quantum")


@guppy.type(
    quantum,
    tys.Opaque(extension="prelude", id="qubit", args=[], bound=TypeBound.Any),
    linear=True,
)
class Qubit:
    pass


def h(q: Qubit) -> Qubit:
    ...


def cx(control: Qubit, target: Qubit) -> tuple[Qubit, Qubit]:
    ...


def measure(q: Qubit) -> tuple[Qubit, bool]:
    ...
