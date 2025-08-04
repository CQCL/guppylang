from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any, Protocol, TypeVar

import numpy as np
import numpy.typing as npt
import selene_sim
from hugr.qsystem.result import QsysResult
from selene_quest_plugin.state import SeleneQuestState, TracedState
from selene_sim.backends.bundled_error_models import IdealErrorModel
from selene_sim.backends.bundled_runtimes import SimpleRuntime
from selene_sim.backends.bundled_simulators import Coinflip, Quest, Stim
from selene_sim.event_hooks import EventHook, NoEventHook
from typing_extensions import Self

if TYPE_CHECKING:
    import datetime
    from collections.abc import Iterator, Sequence
    from pathlib import Path

    from hugr.package import Package
    from hugr.qsystem.result import TaggedResult
    from selene_core import BuildPlanner, QuantumInterface, Utility
    from selene_core.error_model import ErrorModel
    from selene_core.runtime import Runtime
    from selene_core.simulator import Simulator
    from selene_sim.instance import SeleneInstance


__all__ = [
    "EmulatorInstance",
    "EmulatorResult",
    "EmulatorBuilder",
    "TracedState",
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


class EmulatorResult(QsysResult):
    """A result from running an emulator instance."""

    # TODO more docstring

    def partial_states_dict(self) -> list[dict[str, PartialVector]]:
        return [dict(x) for x in self.partial_states()]

    def partial_states(self) -> list[list[tuple[str, PartialVector]]]:
        def to_partial(x: tuple[str, SeleneQuestState]) -> tuple[str, PartialVector]:
            return x[0], PartialVector._from_inner(x[1])

        return [
            list(map(to_partial, Quest.extract_states(shot.entries)))
            for shot in self.results
        ]


@dataclass(frozen=True)
class _Options:
    _simulator: Simulator = field(default_factory=Quest)
    _runtime: Runtime = field(default_factory=SimpleRuntime)
    _error_model: ErrorModel = field(default_factory=IdealErrorModel)
    _shots: int = 1
    _shot_increment: int = 1
    _shot_offset: int = 0
    _seed: int | None = None
    _verbose: bool = False
    _timeout: datetime.timedelta | None = None
    _n_processes: int = 1
    _event_hook: EventHook = field(default_factory=NoEventHook)
    # unstable:
    _results_logfile: Path | None = None


@dataclass(frozen=True)
class EmulatorInstance:
    _instance: SeleneInstance
    _n_qubits: int
    _options: _Options = field(default_factory=_Options)

    def _with_option(self, **kwargs: Any) -> Self:
        """Helper method to simplify setting options."""
        return replace(self, _options=replace(self._options, **kwargs))

    @property
    def n_qubits(self) -> int:
        """Number of qubits available in the emulator instance."""
        return self._n_qubits

    @property
    def shots(self) -> int:
        return self._options._shots

    @property
    def simulator(self) -> Simulator:
        return self._options._simulator

    @property
    def runtime(self) -> Runtime:
        return self._options._runtime

    @property
    def error_model(self) -> ErrorModel:
        return self._options._error_model

    @property
    def verbose(self) -> bool:
        return self._options._verbose

    @property
    def timeout(self) -> datetime.timedelta | None:
        return self._options._timeout

    @property
    def seed(self) -> int | None:
        return self._options._seed

    @property
    def shot_offset(self) -> int:
        return self._options._shot_offset

    @property
    def shot_increment(self) -> int:
        return self._options._shot_increment

    @property
    def n_processes(self) -> int:
        return self._options._n_processes

    def with_n_qubits(self, value: int) -> Self:
        """Update the number of qubits for the emulator instance."""
        return replace(self, _n_qubits=value)

    def with_shots(self, value: int) -> Self:
        return self._with_option(_shots=value)

    def with_simulator(self, value: Simulator) -> Self:
        return self._with_option(_simulator=value)

    def with_runtime(self, value: Runtime) -> Self:
        return self._with_option(_runtime=value)

    def with_error_model(self, value: ErrorModel) -> Self:
        return self._with_option(_error_model=value)

    def with_event_hook(self, value: EventHook) -> Self:
        return self._with_option(_event_hook=value)

    def with_verbose(self, value: bool) -> Self:
        return self._with_option(_verbose=value)

    def with_timeout(self, value: datetime.timedelta | None) -> Self:
        return self._with_option(_timeout=value)

    def with_results_logfile(self, value: Path | None) -> Self:
        return self._with_option(_results_logfile=value)

    def with_seed(self, value: int | None) -> Self:
        new_options = replace(self._options, _seed=value)
        # TODO flaky stateful, remove when selene simplifies
        new_options._simulator.random_seed = value
        out = replace(self, _options=new_options)
        return out

    def with_shot_offset(self, value: int) -> Self:
        return self._with_option(_shot_offset=value)

    def with_shot_increment(self, value: int) -> Self:
        return self._with_option(_shot_increment=value)

    def with_n_processes(self, value: int) -> Self:
        return self._with_option(_n_processes=value)

    def statevector_sim(self) -> Self:
        return self.with_simulator(Quest())

    def coinflip_sim(self) -> Self:
        return self.with_simulator(Coinflip())

    def stabilizer_sim(self) -> Self:
        return self.with_simulator(Stim())

    def run(self) -> EmulatorResult:
        # TODO mention only runs one shot by default
        result_stream = self._run_instance()

        # TODO progress bar on consuming iterator?

        return EmulatorResult(result_stream)

    def _run_instance(self) -> Iterator[Iterator[TaggedResult]]:
        """Run the Selene instance with the given simulator."""
        return self._instance.run_shots(
            simulator=self.simulator,
            n_qubits=self.n_qubits,
            n_shots=self.shots,
            event_hook=self._options._event_hook,
            error_model=self.error_model,
            verbose=self.verbose,
            timeout=self.timeout,
            results_logfile=self._options._results_logfile,
            random_seed=self.seed,
            shot_offset=self.shot_offset,
            shot_increment=self.shot_increment,
            n_processes=self.n_processes,
        )


@dataclass(frozen=True)
class EmulatorBuilder:
    """A builder class for creating EmulatorInstance objects."""

    # interface supported parameters
    _name: str | None = None
    _build_dir: Path | None = None
    _verbose: bool = False

    # selene_sim supported parameters, may be added in the future:
    _planner: BuildPlanner | None = None
    _utilities: Sequence[Utility] | None = None
    _interface: QuantumInterface | None = None
    _progress_bar: bool = False
    _strict: bool = False
    _save_planner: bool = False

    @property
    def name(self) -> str | None:
        return self._name

    @property
    def build_dir(self) -> Path | None:
        return self._build_dir

    @property
    def verbose(self) -> bool:
        return self._verbose

    def with_name(self, value: str | None) -> Self:
        return replace(self, _name=value)

    def with_build_dir(self, value: Path | None) -> Self:
        return replace(self, _build_dir=value)

    def with_verbose(self, value: bool) -> Self:
        return replace(self, _verbose=value)

    def build(self, package: Package, n_qubits: int) -> EmulatorInstance:
        """Build an EmulatorInstance from a compiled package."""

        instance = selene_sim.build(  # type: ignore[attr-defined]
            package,
            name=self._name,
            build_dir=self._build_dir,
            interface=self._interface,
            utilities=self._utilities,
            verbose=self._verbose,
            planner=self._planner,
            progress_bar=self._progress_bar,
            strict=self._strict,
            save_planner=self._save_planner,
        )

        return EmulatorInstance(_instance=instance, _n_qubits=n_qubits)
