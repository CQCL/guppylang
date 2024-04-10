from abc import abstractmethod
from dataclasses import dataclass, field

from guppylang.definition.common import CompiledDef, Definition
from guppylang.tys.param import Parameter, TypeParam


class ParamDef(Definition):
    """Abstract base class for type parameter definitions."""

    @abstractmethod
    def to_param(self, idx: int) -> Parameter:
        """Creates a parameter from this definition."""


@dataclass(frozen=True)
class TypeVarDef(ParamDef, CompiledDef):  # Inherit from
    """A type variable definition."""

    can_be_linear: bool

    description: str = field(default="type variable", init=False)

    def to_param(self, idx: int) -> TypeParam:
        """Creates a parameter from this definition."""
        return TypeParam(idx, self.name, self.can_be_linear)
