"""
Emulation of Guppy programs powered by the selene-sim package.

Provides a configurable interface for compiling Guppy functions
into an emulator instance, and a configurable builder for setting
instance options and executing.

Emulation returns py:class:`EmulatorResult` objects, which contain the result output
by the emulation.

"""

from .builder import EmulatorBuilder
from .instance import EmulatorInstance
from .result import EmulatorResult
from .state import PartialState, PartialVector, StateVector, TracedState

__all__ = [
    "EmulatorInstance",
    "EmulatorResult",
    "EmulatorBuilder",
    "PartialVector",
    "PartialState",
    "StateVector",
    "TracedState",
]
