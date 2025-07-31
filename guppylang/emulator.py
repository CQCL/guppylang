from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

import selene_sim
from hugr.qsystem.result import QsysResult
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
    "EmulatorOpts",
    "EmulatorResult",
    "EmulatorBuilder",
    "selene_sim",
]


class EmulatorResult(QsysResult):
    """A result from running an emulator instance."""

    # TODO more docstring


@dataclass(frozen=True)
class EmulatorOpts:
    _n_shots: int = 1
    _simulator: Simulator = field(default_factory=Coinflip)
    _runtime: Runtime = field(default_factory=SimpleRuntime)
    _error_model: ErrorModel = field(default_factory=IdealErrorModel)
    _event_hook: EventHook = field(default_factory=NoEventHook)
    _verbose: bool = False
    _timeout: datetime.timedelta | None = None
    _results_logfile: Path | None = None
    _random_seed: int | None = None
    _shot_offset: int = 0
    _shot_increment: int = 1
    _n_processes: int = 1

    @property
    def n_shots(self) -> int:
        return self._n_shots

    @property
    def simulator(self) -> Simulator:
        return self._simulator

    @property
    def runtime(self) -> Runtime:
        return self._runtime

    @property
    def error_model(self) -> ErrorModel:
        return self._error_model

    @property
    def event_hook(self) -> EventHook:
        return self._event_hook

    @property
    def verbose(self) -> bool:
        return self._verbose

    @property
    def timeout(self) -> datetime.timedelta | None:
        return self._timeout

    @property
    def results_logfile(self) -> Path | None:
        return self._results_logfile

    @property
    def random_seed(self) -> int | None:
        return self._random_seed

    @property
    def shot_offset(self) -> int:
        return self._shot_offset

    @property
    def shot_increment(self) -> int:
        return self._shot_increment

    @property
    def n_processes(self) -> int:
        return self._n_processes

    def with_n_shots(self, value: int) -> Self:
        return replace(self, _n_shots=value)

    def with_simulator(self, value: Simulator) -> Self:
        return replace(self, _simulator=value)

    def with_runtime(self, value: Runtime) -> Self:
        return replace(self, _runtime=value)

    def with_error_model(self, value: ErrorModel) -> Self:
        return replace(self, _error_model=value)

    def with_event_hook(self, value: EventHook) -> Self:
        return replace(self, _event_hook=value)

    def with_verbose(self, value: bool) -> Self:
        return replace(self, _verbose=value)

    def with_timeout(self, value: datetime.timedelta | None) -> Self:
        return replace(self, _timeout=value)

    def with_results_logfile(self, value: Path | None) -> Self:
        return replace(self, _results_logfile=value)

    def with_random_seed(self, value: int | None) -> Self:
        out = replace(self, _random_seed=value)
        # TODO flaky stateful, remove when selene simplifies
        out.simulator.random_seed = value
        return out

    def with_shot_offset(self, value: int) -> Self:
        return replace(self, _shot_offset=value)

    def with_shot_increment(self, value: int) -> Self:
        return replace(self, _shot_increment=value)

    def with_n_processes(self, value: int) -> Self:
        return replace(self, _n_processes=value)

    @classmethod
    def statevector(cls) -> Self:
        return cls().with_simulator(Quest())

    @classmethod
    def coinflip(cls) -> Self:
        return cls().with_simulator(Coinflip())

    @classmethod
    def stabilizer(cls) -> Self:
        return cls().with_simulator(Stim())


@dataclass
class EmulatorInstance:
    _instance: SeleneInstance

    def run(self, n_qubits: int, options: EmulatorOpts | None = None) -> EmulatorResult:
        result_stream = self._run_instance(n_qubits=n_qubits, options=options)

        # TODO progress bar on consuming iterator?

        return EmulatorResult(result_stream)

    def _run_instance(
        self, n_qubits: int, options: EmulatorOpts | None = None
    ) -> Iterator[Iterator[TaggedResult]]:
        """Run the Selene instance with the given simulator."""
        options = options or EmulatorOpts()

        return self._instance.run_shots(
            simulator=options.simulator,
            n_qubits=n_qubits,
            n_shots=options.n_shots,
            event_hook=options.event_hook,
            error_model=options.error_model,
            verbose=options.verbose,
            timeout=options.timeout,
            results_logfile=options.results_logfile,
            random_seed=options.random_seed,
            shot_offset=options.shot_offset,
            shot_increment=options.shot_increment,
            n_processes=options.n_processes,
        )


@dataclass(frozen=True)
class EmulatorBuilder:
    """A builder class for creating EmulatorInstance objects."""

    # interface supported parameters
    _name: str | None = None
    _build_dir: Path | None = None
    _verbose: bool = False

    # selene_sim supported parameters, may be added in the future
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

    def build(self, package: Package) -> EmulatorInstance:
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

        return EmulatorInstance(_instance=instance)
