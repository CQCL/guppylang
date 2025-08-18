
from dataclasses import dataclass
from typing import Sequence

from guppylang_internals.definition.common import DefId
from guppylang_internals.tys.arg import Argument
# from guppylang_internals.tys.subst import Subst

@dataclass(frozen=True)
class ProtocolInst():
    type_args: Sequence[Argument]
    definition: DefId

    def substitute(self, subst: "Subst") -> "ProtocolInst":
        # TODO: not this
        return self
