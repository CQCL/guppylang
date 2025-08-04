from __future__ import annotations

from typing import TYPE_CHECKING

from hugr.qsystem.result import QsysResult
from selene_sim.backends.bundled_simulators import Quest

from .state import PartialVector

if TYPE_CHECKING:
    from selene_quest_plugin.state import SeleneQuestState


class EmulatorResult(QsysResult):
    """A result from running an emulator instance."""

    # TODO more docstring

    def partial_state_dicts(self) -> list[dict[str, PartialVector]]:
        return [dict(x) for x in self.partial_states()]

    def partial_states(self) -> list[list[tuple[str, PartialVector]]]:
        def to_partial(x: tuple[str, SeleneQuestState]) -> tuple[str, PartialVector]:
            return x[0], PartialVector._from_inner(x[1])

        return [
            list(map(to_partial, Quest.extract_states(shot.entries)))
            for shot in self.results
        ]
