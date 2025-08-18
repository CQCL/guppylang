from dataclasses import dataclass
from typing import Mapping, Sequence

from guppylang_internals.definition.common import Definition
from guppylang_internals.tys.param import Parameter
from guppylang_internals.tys.ty import FunctionType


@dataclass(frozen=True)
class CheckedProtocolDef(Definition):
    type_params: Sequence[Parameter]
    members: Mapping[str, FunctionType]

    @property
    def description(self) -> str:
        return ""
