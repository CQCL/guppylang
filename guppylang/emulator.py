from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

import selene_sim
from hugr.qsystem.result import QsysResult
from selene_core.simulator import Simulator
from selene_sim.backends.bundled_error_models import IdealErrorModel
from selene_sim.backends.bundled_simulators import (
    ClassicalReplay,
    Coinflip,
    Quest,
    Stim,
)
from selene_sim.event_hooks import EventHook, NoEventHook

if TYPE_CHECKING:
    import datetime
    from collections.abc import Iterator, Sequence
    from pathlib import Path

    from hugr.package import Package
    from hugr.qsystem.result import TaggedResult
    from selene_core import BuildPlanner, QuantumInterface, Utility
    from selene_core.error_model import ErrorModel
    from selene_sim.instance import SeleneInstance


__all__ = [
    "EmulatorInstance",
    "EmulatorOptions",
    "EmulatorResult",
    "Simulator",
    "selene_sim",
]


@dataclass(frozen=True)
class EmulatorResult:
    _qsys_result: QsysResult


class Config(Protocol):
    def update(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise ValueError(f"Invalid configuration key: {key}")


@dataclass
class EmulatorOptions(Config):
    error_model: ErrorModel = field(default_factory=IdealErrorModel)
    event_hook: EventHook = field(default_factory=NoEventHook)
    verbose: bool = False
    timeout: datetime.timedelta | None = None
    results_logfile: Path | None = None
    random_seed: int | None = None
    shot_offset: int = 0
    shot_increment: int = 1
    n_processes: int = 1


@dataclass
class EmulatorInstance:
    _instance: SeleneInstance
    n_qubits: int
    options: EmulatorOptions = field(default_factory=EmulatorOptions)

    def run(self, simulator: Simulator, n_shots: int = 1) -> EmulatorResult:
        result_stream = self._run_instance(
            simulator=simulator, n_qubits=self.n_qubits, n_shots=n_shots
        )

        # TODO progress bar on consuming iterator?

        qsys_res = QsysResult(result_stream)
        return EmulatorResult(_qsys_result=qsys_res)

    def run_statevector(self, n_shots: int = 1) -> EmulatorResult:
        """Run with the default statevector simulation backend."""
        return self.run(simulator=Quest(self.options.random_seed), n_shots=n_shots)

    def run_stabilizer(self, n_shots: int = 1) -> EmulatorResult:
        """Run with the default stabilizer simulation backend."""
        return self.run(simulator=Stim(self.options.random_seed), n_shots=n_shots)

    def run_coinflip(self, n_shots: int = 1) -> EmulatorResult:
        """Run with the default coinflip simulation backend."""
        return self.run(
            simulator=Coinflip(random_seed=self.options.random_seed), n_shots=n_shots
        )

    def run_classical_replay(
        self, measurements: Sequence[Sequence[bool]], n_shots: int = 1
    ) -> EmulatorResult:
        """Run with the default classical replay simulation backend."""
        return self.run(
            simulator=ClassicalReplay(
                measurements=list(map(list, measurements)),
                random_seed=self.options.random_seed,
            ),
            n_shots=n_shots,
        )

    def _run_instance(
        self, simulator: Simulator, n_qubits: int, n_shots: int
    ) -> Iterator[Iterator[TaggedResult]]:
        """Run the Selene instance with the given simulator."""
        return self._instance.run_shots(
            simulator=simulator,
            n_qubits=n_qubits,
            n_shots=n_shots,
            event_hook=self.options.event_hook,
            error_model=self.options.error_model,
            verbose=self.options.verbose,
            timeout=self.options.timeout,
            results_logfile=self.options.results_logfile,
            random_seed=self.options.random_seed,
            shot_offset=self.options.shot_offset,
            shot_increment=self.options.shot_increment,
            n_processes=self.options.n_processes,
        )

    def set_seed(self, seed: int) -> None:
        """Set the random seed for the emulator instance."""
        self.options.random_seed = seed


@dataclass
class EmulatorBuilder(Config):
    """A builder class for creating EmulatorInstance objects."""

    name: str | None = None
    build_dir: Path | None = None
    interface: QuantumInterface | None = None
    utilities: Sequence[Utility] | None = None
    verbose: bool = False
    planner: BuildPlanner | None = None
    progress_bar: bool = False
    strict: bool = False
    save_planner: bool = False

    def build(self, package: Package, n_qubits: int) -> EmulatorInstance:
        """Build an EmulatorInstance from a compiled package."""

        instance = selene_sim.build(  # type: ignore[attr-defined]
            package,
            name=self.name,
            build_dir=self.build_dir,
            interface=self.interface,
            utilities=self.utilities,
            verbose=self.verbose,
            planner=self.planner,
            progress_bar=self.progress_bar,
            strict=self.strict,
            save_planner=self.save_planner,
        )

        return EmulatorInstance(_instance=instance, n_qubits=n_qubits)
