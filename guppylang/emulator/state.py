from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypeVar

import numpy as np
import numpy.typing as npt
from selene_quest_plugin.state import SeleneQuestState, TracedState
from typing_extensions import Self

__all__ = [
    "TracedState",
    "NotSingleStateError",
    "PartialState",
    "PartialVector",
    "StateVector",
]

# Type encoding a single state. e.g. StateVector for a state vector.
S = TypeVar("S")

StateVector = npt.NDArray[np.complexfloating]


@dataclass(frozen=True)
class NotSingleStateError(Exception):
    """Raised when a Selene state is not a single state, i.e. it has unspecified qubits
    that have been traced out."""

    total_qubits: int
    n_specified_qubits: int

    def __str__(self) -> str:
        return (
            f"Selene state is not a single state: "
            f"total qubits {self.total_qubits} != "
            f"specified qubits {self.n_specified_qubits}."
        )


class PartialState(Protocol[S]):
    """Protocol for an emulator state type.
    Different simulation backends may have different state representations."""

    @property
    def total_qubits(self) -> int:
        """Total number of qubits in the state."""
        ...

    @property
    def specified_qubits(self) -> list[int]:
        """List of specified qubits in the state."""
        ...

    def state_distribution(self, zero_threshold: float = 1e-12) -> list[TracedState[S]]:
        """Distribution of states after tracing out unspecified qubits."""
        ...

    def as_single_state(self, zero_threshold: float = 1e-12) -> S:
        """If no qubits are traced out (len(specified_qubits) == total_qubits),
        return the state as a single state vector."""
        if len(self.specified_qubits) != self.total_qubits:
            raise NotSingleStateError(
                total_qubits=self.total_qubits,
                n_specified_qubits=len(self.specified_qubits),
            )
        all_states = self.state_distribution(zero_threshold)
        assert len(all_states) == 1, "Expected exactly one state in the distribution."
        return all_states[0].state


class PartialVector(PartialState[StateVector]):
    """Partial state vector for simulator backends with statevector representation."""

    _inner: SeleneQuestState

    def __init__(
        self, base_state: StateVector, total_qubits: int, specified_qubits: list[int]
    ) -> None:
        self._inner = SeleneQuestState(
            state=base_state,
            total_qubits=total_qubits,
            specified_qubits=specified_qubits,
        )

    @property
    def total_qubits(self) -> int:
        """Total number of qubits in the state."""
        return self._inner.total_qubits

    @property
    def specified_qubits(self) -> list[int]:
        """List of specified qubits in the state."""
        return self._inner.specified_qubits

    def state_distribution(
        self, zero_threshold: float = 1e-12
    ) -> list[TracedState[StateVector]]:
        return self._inner.get_state_vector_distribution(zero_threshold=zero_threshold)

    def as_single_state(self, zero_threshold: float = 1e-12) -> StateVector:
        return self._inner.get_single_state(zero_threshold=zero_threshold)

    @classmethod
    def _from_inner(cls, inner: SeleneQuestState) -> Self:
        """Create a PartialVector from an inner SeleneQuestState."""
        obj = cls.__new__(cls)
        obj._inner = inner
        return obj
