from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, TypeAlias

from hugr import tys as ht
from typing_extensions import Self

from guppylang.ast_util import AstNode
from guppylang.checker.errors.generic import ExpectedError
from guppylang.checker.errors.type_errors import TypeMismatchError
from guppylang.error import GuppyError, GuppyTypeError, InternalGuppyError
from guppylang.tys.arg import Argument, ConstArg, TypeArg
from guppylang.tys.common import ToHugr, ToHugrContext
from guppylang.tys.const import BoundConstVar, ExistentialConstVar
from guppylang.tys.errors import WrongNumberOfTypeArgsError
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
class ParameterBase(ToHugr[ht.TypeParam], ABC):
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

    must_be_copyable: bool
    must_be_droppable: bool

    @property
    def can_be_linear(self) -> bool:
        """Whether this type should be treated linearly."""
        return not self.must_be_copyable and not self.must_be_droppable

    def with_idx(self, idx: int) -> "TypeParam":
        """Returns a copy of the parameter with a new index."""
        return TypeParam(idx, self.name, self.must_be_copyable, self.must_be_droppable)

    def check_arg(self, arg: Argument, loc: AstNode | None = None) -> TypeArg:
        """Checks that this parameter can be instantiated with a given argument.

        Raises a user error if the argument is not valid.
        """
        match arg:
            case ConstArg(const):
                err = ExpectedError(loc, "a type", got=f"value of type `{const.ty}`")
                raise GuppyTypeError(err)
            case TypeArg(ty):
                if self.must_be_copyable and not ty.copyable:
                    err = ExpectedError(
                        loc,
                        "a copyable type",
                        got=f"type `{ty}` which is not implicitly copyable",
                    )
                    raise GuppyTypeError(err)
                if self.must_be_droppable and not ty.droppable:
                    err = ExpectedError(
                        loc,
                        "a droppable type",
                        got=f"type `{ty}` which is not implicitly droppable",
                    )
                    raise GuppyTypeError(err)
                return arg

    def to_existential(self) -> tuple[Argument, ExistentialVar]:
        """Creates a fresh existential variable that can be instantiated for this
        parameter.

        Returns both the argument and the created variable.
        """
        from guppylang.tys.ty import ExistentialTypeVar

        var = ExistentialTypeVar.fresh(
            self.name, self.must_be_copyable, self.must_be_droppable
        )
        return TypeArg(var), var

    def to_bound(self, idx: int | None = None) -> TypeArg:
        """Creates a bound variable with a given index that can be instantiated for this
        parameter.
        """
        from guppylang.tys.ty import BoundTypeVar

        if idx is None:
            idx = self.idx
        return TypeArg(
            BoundTypeVar(self.name, idx, self.must_be_copyable, self.must_be_droppable)
        )

    def to_hugr(self, ctx: ToHugrContext) -> ht.TypeParam:
        """Computes the Hugr representation of the parameter."""
        return ht.TypeTypeParam(
            bound=ht.TypeBound.Linear if self.can_be_linear else ht.TypeBound.Copyable
        )

    def __str__(self) -> str:
        """User-facing string representation of the parameter."""
        return self.name


@dataclass(frozen=True)
class ConstParam(ParameterBase):
    """A parameter of kind constant. Used to define fixed-size arrays etc."""

    ty: "Type"

    #: Marker to annotate if this parameter was implicitly generated by a `@comptime`
    #: annotated argument in a function signature.
    from_comptime_arg: bool = field(default=False, kw_only=True)

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
                        TypeMismatchError(loc, self.ty, const.ty, kind="argument")
                    )
                return arg
            case TypeArg(ty=ty):
                err = ExpectedError(
                    loc, f"expression of type `{self.ty}`", got=f"type `{ty}`"
                )
                raise GuppyTypeError(err)

    def to_existential(self) -> tuple[Argument, ExistentialVar]:
        """Creates a fresh existential variable that can be instantiated for this
        parameter.

        Returns both the argument and the created variable.
        """
        var = ExistentialConstVar.fresh(self.name, self.ty)
        return ConstArg(var), var

    def to_bound(self, idx: int | None = None) -> ConstArg:
        """Creates a bound variable with a given index that can be instantiated for this
        parameter.
        """
        if idx is None:
            idx = self.idx
        return ConstArg(BoundConstVar(self.ty, self.name, idx))

    def to_hugr(self, ctx: ToHugrContext) -> ht.TypeParam:
        """Computes the Hugr representation of the parameter."""
        from guppylang.tys.ty import NumericType

        match self.ty:
            case NumericType(kind=NumericType.Kind.Nat):
                return ht.BoundedNatParam(upper_bound=None)
            case _:
                raise InternalGuppyError(
                    "Tried to convert non-nat const type parameter to Hugr. This "
                    "should have been monomorphized away."
                )

    def __str__(self) -> str:
        """User-facing string representation of the parameter."""
        return f"{self.name}: {self.ty}"


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
    if exp != act:
        # TODO: Adjust the error span to only point to the offending arguments (similar
        #  to how we deal with call args in the expression checker). This requires
        #  threading the type arg spans down to this point
        raise GuppyError(WrongNumberOfTypeArgsError(loc, exp, act, type_name))

    # Now check that the kinds match up
    for param, arg in zip(params, args, strict=True):
        # TODO: The error location is bad. We want the location of `arg`, not of the
        #  whole thing.
        param.check_arg(arg, loc)
