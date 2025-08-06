
from dataclasses import dataclass
from typing import Sequence

from guppylang.definition.common import DefId
from guppylang.tys.arg import Argument
from guppylang.tys.subst import Subst


@dataclass(frozen=True)
class ProtocolInst():
    type_args: Sequence[Argument]
    definition: DefId

    def substitute(self, subst: Subst) -> "ProtocolInst":
        # TODO
        pass