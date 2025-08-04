from dataclasses import dataclass
from typing import Mapping, Sequence

from guppylang.definition.common import CheckedDef
from guppylang.tys.param import Parameter
from guppylang.tys.ty import FunctionType


@dataclass(frozen=True)
class CheckedProtocolDef(CheckedDef):
    type_params: Sequence[Parameter]
    members: Mapping[str, FunctionType]