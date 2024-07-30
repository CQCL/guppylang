from abc import abstractmethod
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, TypeAlias

from hugr.serialization import tys

from guppylang.ast_util import AstNode
from guppylang.definition.common import CompiledDef, Definition
from guppylang.error import GuppyError
from guppylang.tys.arg import Argument
from guppylang.tys.param import Parameter, check_all_args
from guppylang.tys.ty import InputFlags, OpaqueType, Type

if TYPE_CHECKING:
    from guppylang.checker.core import Globals


FlaggedArgs: TypeAlias = Sequence[tuple[Argument, InputFlags]]


@dataclass(frozen=True)
class TypeDef(Definition):
    """Abstract base class for type definitions."""

    description: str = field(default="type", init=False)

    @abstractmethod
    def check_instantiate(
        self, args: FlaggedArgs, globals: "Globals", loc: AstNode | None = None
    ) -> Type:
        """Checks if the type definition can be instantiated with the given arguments.

        Returns the resulting concrete type or raises a user error if the arguments are
        invalid.
        """


@dataclass(frozen=True)
class OpaqueTypeDef(TypeDef, CompiledDef):
    """An opaque type definition that is backed by some Hugr type."""

    params: Sequence[Parameter]
    always_linear: bool
    to_hugr: Callable[[Sequence[Argument]], tys.Type]
    bound: tys.TypeBound | None = None

    def check_instantiate(
        self, args: FlaggedArgs, globals: "Globals", loc: AstNode | None = None
    ) -> OpaqueType:
        """Checks if the type definition can be instantiated with the given arguments.

        Returns the resulting concrete type or raises a user error if the arguments are
        invalid.
        """
        args = check_no_flags(args, loc)
        check_all_args(self.params, args, self.name, loc)
        return OpaqueType(args, self)


def check_no_flags(args: FlaggedArgs, loc: AstNode | None) -> list[Argument]:
    """Checks that no argument to `check_instantiate` has any `@flags`."""
    for _, flags in args:
        if flags != InputFlags.NoFlags:
            raise GuppyError(
                "`@` type annotations are not allowed in this position", loc
            )
    return [ty for ty, _ in args]
