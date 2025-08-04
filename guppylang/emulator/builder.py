from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

import selene_sim
from typing_extensions import Self

from .instance import EmulatorInstance

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from hugr.package import Package
    from selene_core import BuildPlanner, QuantumInterface, Utility


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
