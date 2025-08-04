"""
Emulator module for GuppyLang.

This module provides classes for building and executing emulators that can run
Guppy programs. It includes functionality for extracting emulator state,
building and configuring emulator instances, and processing emulation results.
"""

from .builder import EmulatorBuilder
from .instance import EmulatorInstance
from .result import EmulatorResult
from .state import PartialVector, StateVector, TracedState

__all__ = [
    "EmulatorInstance",
    "EmulatorResult",
    "EmulatorBuilder",
    "TracedState",
    "PartialVector",
    "StateVector",
]
