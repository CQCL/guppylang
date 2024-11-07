from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeAlias

from hugr import tys as ht

from guppylang.error import InternalGuppyError
from guppylang.tys.common import ToHugr, Transformable, Transformer, Visitor
from guppylang.tys.const import BoundConstVar, Const, ConstValue, ExistentialConstVar
from guppylang.tys.var import ExistentialVar

if TYPE_CHECKING:
    from guppylang.tys.ty import Type


# We define the `Argument` type as a union of all `ArgumentBase` subclasses defined
# below. This models an algebraic data type and enables exhaustiveness checking in
# pattern matches etc.
# Note that this might become obsolete in case the `@sealed` decorator is added:
#  * https://peps.python.org/pep-0622/#sealed-classes-as-algebraic-data-types
#  * https://github.com/johnthagen/sealed-typing-pep
Argument: TypeAlias = "TypeArg | ConstArg"


@dataclass(frozen=True)
class ArgumentBase(ToHugr[ht.TypeArg], Transformable["Argument"], ABC):
    """Abstract base class for arguments of parametrized types.

    For example, in the type `array[int, 42]` we have two arguments `int` and `42`.
    """

    @property
    @abstractmethod
    def unsolved_vars(self) -> set[ExistentialVar]:
        """The existential type variables contained in this argument."""


@dataclass(frozen=True)
class TypeArg(ArgumentBase):
    """Argument that can be instantiated for a `TypeParameter`."""

    # The type to instantiate
    ty: "Type"

    @property
    def unsolved_vars(self) -> set[ExistentialVar]:
        """The existential type variables contained in this argument."""
        return self.ty.unsolved_vars

    def to_hugr(self) -> ht.TypeTypeArg:
        """Computes the Hugr representation of the argument."""
        ty: ht.Type = self.ty.to_hugr()
        return ty.type_arg()

    def visit(self, visitor: Visitor) -> None:
        """Accepts a visitor on this argument."""
        if not visitor.visit(self):
            self.ty.visit(visitor)

    def transform(self, transformer: Transformer) -> Argument:
        """Accepts a transformer on this argument."""
        return transformer.transform(self) or TypeArg(self.ty.transform(transformer))


@dataclass(frozen=True)
class ConstArg(ArgumentBase):
    """Argument that can be substituted for a `ConstParam`."""

    const: Const

    @property
    def unsolved_vars(self) -> set[ExistentialVar]:
        """The existential const variables contained in this argument."""
        return self.const.unsolved_vars

    def to_hugr(self) -> ht.TypeArg:
        """Computes the Hugr representation of this argument."""
        from guppylang.tys.ty import NumericType

        match self.const:
            case ConstValue(value=v, ty=NumericType(kind=NumericType.Kind.Nat)):
                assert isinstance(v, int)
                return ht.BoundedNatArg(n=v)
            case BoundConstVar(idx=idx, ty=NumericType(kind=NumericType.Kind.Nat)):
                param = ht.BoundedNatParam(upper_bound=None)
                return ht.VariableArg(idx=idx, param=param)
            case ConstValue() | BoundConstVar():
                # TODO: Handle other cases besides nats
                raise NotImplementedError
            case ExistentialConstVar():
                raise InternalGuppyError(
                    "Tried to convert unsolved constant variable to Hugr"
                )

    def visit(self, visitor: Visitor) -> None:
        """Accepts a visitor on this argument."""
        visitor.visit(self)

    def transform(self, transformer: Transformer) -> Argument:
        """Accepts a transformer on this argument."""
        return transformer.transform(self) or ConstArg(
            self.const.transform(transformer)
        )
