from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeAlias

from hugr.serialization import tys
from hugr.serialization.tys import TypeBound
from typing_extensions import Self

from guppylang.ast_util import AstNode
from guppylang.error import GuppyError, GuppyTypeError, InternalGuppyError
from guppylang.tys.arg import Argument, ConstArg, TypeArg
from guppylang.tys.common import ToHugr
from guppylang.tys.const import BoundConstVar, ExistentialConstVar
from guppylang.tys.var import ExistentialVar

if TYPE_CHECKING:
    from guppylang.tys.ty import Type


# We define the `Parameter` type as a union of all `ParameterBase` subclasses defined
# below. This models an algebraic data type and enables exhaustiveness checking in
# pattern matches etc.
# Note that this might become obsolete in case the `@sealed` decorator is added:
#  * https://peps.python.org/pep-0622/#sealed-classes-as-algebraic-data-types
#  * https://github.com/johnthagen/sealed-typing-pep
Parameter: TypeAlias = "TypeParam | ConstParam"


@dataclass(frozen=True)
class ParameterBase(ToHugr[tys.TypeParam], ABC):
    """Abstract base class for parameters used in function and type definitions.

    For example, when defining a struct type

    ```
    @guppy.struct
    class Foo[T, n: int]:
        ...
    ```

    we generate an `StructDef` that depends on the parameters `T` and `n`. From
    this, we obtain a proper `StructType` by providing arguments that are substituted
    for the parameters (for example `Foo[int, 42]`).
    """

    idx: int
    name: str

    @abstractmethod
    def with_idx(self, idx: int) -> Self:
        """Returns a copy of the parameter with a new index."""

    @abstractmethod
    def check_arg(self, arg: Argument, loc: AstNode | None = None) -> Argument:
        """Checks that this parameter can be instantiated with a given argument.

        Raises a user error if the argument is not valid.
        """

    @abstractmethod
    def to_existential(self) -> tuple[Argument, ExistentialVar]:
        """Creates a fresh existential variable that can be instantiated for this
        parameter.

        Returns both the argument and the created variable.
        """

    @abstractmethod
    def to_bound(self, idx: int | None = None) -> Argument:
        """Creates a bound variable with a given index that can be instantiated for this
        parameter.
        """


@dataclass(frozen=True)
class TypeParam(ParameterBase):
    """A parameter of kind type. Used to define generic functions and types."""

    can_be_linear: bool

    def with_idx(self, idx: int) -> "TypeParam":
        """Returns a copy of the parameter with a new index."""
        return TypeParam(idx, self.name, self.can_be_linear)

    def check_arg(self, arg: Argument, loc: AstNode | None = None) -> TypeArg:
        """Checks that this parameter can be instantiated with a given argument.

        Raises a user error if the argument is not valid.
        """
        match arg:
            case ConstArg(const):
                raise GuppyTypeError(
                    f"Expected a type, got value of type {const.ty}", loc
                )
            case TypeArg(ty):
                if not self.can_be_linear and ty.linear:
                    raise GuppyTypeError(
                        f"Expected a non-linear type, got value of type {ty}", loc
                    )
                return arg

    def to_existential(self) -> tuple[Argument, ExistentialVar]:
        """Creates a fresh existential variable that can be instantiated for this
        parameter.

        Returns both the argument and the created variable.
        """
        from guppylang.tys.ty import ExistentialTypeVar

        var = ExistentialTypeVar.fresh(self.name, self.can_be_linear)
        return TypeArg(var), var

    def to_bound(self, idx: int | None = None) -> Argument:
        """Creates a bound variable with a given index that can be instantiated for this
        parameter.
        """
        from guppylang.tys.ty import BoundTypeVar

        if idx is None:
            idx = self.idx
        return TypeArg(BoundTypeVar(self.name, idx, self.can_be_linear))

    def to_hugr(self) -> tys.TypeParam:
        """Computes the Hugr representation of the parameter."""
        return tys.TypeParam(
            tys.TypeTypeParam(
                b=tys.TypeBound.Any if self.can_be_linear else TypeBound.Copyable
            )
        )


@dataclass(frozen=True)
class ConstParam(ParameterBase):
    """A parameter of kind constant. Used to define fixed-size arrays etc."""

    ty: "Type"

    def __post_init__(self) -> None:
        if self.ty.unsolved_vars:
            raise InternalGuppyError(
                "Attempted to create constant param with unsolved type"
            )

    def with_idx(self, idx: int) -> "ConstParam":
        """Returns a copy of the parameter with a new index."""
        return ConstParam(idx, self.name, self.ty)

    def check_arg(self, arg: Argument, loc: AstNode | None = None) -> ConstArg:
        """Checks that this parameter can be instantiated with a given argument.

        Raises a user error if the argument is not valid.
        """
        match arg:
            case ConstArg(const):
                if const.ty != self.ty:
                    raise GuppyTypeError(
                        f"Expected argument of type `{self.ty}`, got {const.ty}", loc
                    )
                return arg
            case TypeArg():
                raise GuppyTypeError(
                    f"Expected argument of type `{self.ty}`, got type", loc
                )

    def to_existential(self) -> tuple[Argument, ExistentialVar]:
        """Creates a fresh existential variable that can be instantiated for this
        parameter.

        Returns both the argument and the created variable.
        """
        var = ExistentialConstVar.fresh(self.name, self.ty)
        return ConstArg(var), var

    def to_bound(self, idx: int | None = None) -> Argument:
        """Creates a bound variable with a given index that can be instantiated for this
        parameter.
        """
        if idx is None:
            idx = self.idx
        return ConstArg(BoundConstVar(self.ty, self.name, idx))

    def to_hugr(self) -> tys.TypeParam:
        """Computes the Hugr representation of the parameter."""
        from guppylang.tys.ty import NumericType

        match self.ty:
            case NumericType(kind=NumericType.Kind.Nat):
                return tys.TypeParam(tys.BoundedNatParam(bound=None))
            case _:
                hugr_ty = self.ty.to_hugr()
                assert isinstance(hugr_ty.root, tys.Opaque)
                return tys.TypeParam(tys.OpaqueParam(ty=hugr_ty.root))


def check_all_args(
    params: Sequence[Parameter],
    args: Sequence[Argument],
    type_name: str,
    loc: AstNode | None = None,
) -> None:
    """Checks a list of arguments against the given parameters.

    Raises a user error if number of arguments doesn't match or one of the argument is
    invalid.
    """
    exp, act = len(params), len(args)
    if exp > act:
        raise GuppyError(f"Missing parameter for type `{type_name}`", loc)
    elif 0 == exp < act:
        raise GuppyError(f"Type `{type_name}` is not parameterized", loc)
    elif 0 < exp < act:
        raise GuppyError(f"Too many parameters for type `{type_name}`", loc)

    # Now check that the kinds match up
    for param, arg in zip(params, args, strict=True):
        # TODO: The error location is bad. We want the location of `arg`, not of the
        #  whole thing.
        param.check_arg(arg, loc)
