
from dataclasses import dataclass
from typing import Sequence

from guppylang_internals.definition.common import DefId
from guppylang_internals.tys.arg import Argument

@dataclass(frozen=True)
class ProtocolInst():
    type_args: Sequence[Argument]
    definition: DefId

    def substitute(self, subst: "Subst") -> "ProtocolInst":
        # TODO
        pass