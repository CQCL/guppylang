
from dataclasses import dataclass
from typing import Sequence

from guppylang.definition.common import DefId
from guppylang.tys.arg import Argument


@dataclass(frozen=True)
class ProtocolInst():
    type_args: Sequence[Argument]
    definition: DefId