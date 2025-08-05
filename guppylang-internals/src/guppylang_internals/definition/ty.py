from abc import abstractmethod
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from hugr import tys

from guppylang_internals.ast_util import AstNode
from guppylang_internals.definition.common import CompiledDef, Definition
from guppylang_internals.tys.arg import Argument
from guppylang_internals.tys.common import ToHugrContext
from guppylang_internals.tys.param import Parameter, check_all_args
from guppylang_internals.tys.ty import OpaqueType, Type


@dataclass(frozen=True)
class TypeDef(Definition):
    """Abstract base class for type definitions."""

    description: str = field(default="type", init=False)

    @abstractmethod
    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> Type:
        """Checks if the type definition can be instantiated with the given arguments.

        Returns the resulting concrete type or raises a user error if the arguments are
        invalid.
        """


@dataclass(frozen=True)
class OpaqueTypeDef(TypeDef, CompiledDef):
    """An opaque type definition that is backed by some Hugr type."""

    params: Sequence[Parameter]
    never_copyable: bool
    never_droppable: bool
    to_hugr: Callable[[Sequence[Argument], ToHugrContext], tys.Type]
    bound: tys.TypeBound | None = None

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> OpaqueType:
        """Checks if the type definition can be instantiated with the given arguments.

        Returns the resulting concrete type or raises a user error if the arguments are
        invalid.
        """
        check_all_args(self.params, args, self.name, loc)
        return OpaqueType(args, self)
