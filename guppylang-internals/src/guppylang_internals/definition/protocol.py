import ast
from dataclasses import dataclass
from typing import Mapping, Sequence

from guppylang_internals.definition.common import CheckableDef, Definition
from guppylang_internals.tys.param import Parameter
from guppylang_internals.tys.ty import FunctionType

@dataclass(frozen=True)
class ParsedProtocolDef(CheckableDef):
    defined_at: ast.ClassDef
    params: Sequence[Parameter]
    members: Sequence["UncheckedStructField"]

@dataclass(frozen=True)
class CheckedProtocolDef(Definition):
    defined_at: ast.ClassDef
    params: Sequence[Parameter]
    members: Mapping[str, FunctionType]

    @property
    def description(self) -> str:
        return ""
