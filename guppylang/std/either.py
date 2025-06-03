"""Union of two types.

Type `Either[L, R]` represents a value of either typr `L` ("left") or `R` ("right").
"""

from typing import Generic, no_type_check

from guppylang.decorator import guppy
from guppylang.std._internal.compiler.either import (
    EitherConstructor,
    EitherTestCompiler,
    EitherToOptionCompiler,
    EitherUnwrapCompiler,
    either_to_hugr,
)
from guppylang.std.builtins import owned
from guppylang.std.option import Option
from guppylang.tys.param import TypeParam

L = guppy.type_var("L", copyable=False, droppable=False)
R = guppy.type_var("R", copyable=False, droppable=False)
Droppable = guppy.type_var("Droppable", copyable=False, droppable=True)

_params = [TypeParam(0, "L", False, False), TypeParam(1, "L", False, False)]


@guppy.type(either_to_hugr, params=_params)
class Either(Generic[L, R]):  # type: ignore[misc]
    """Represents a union of either a `left` or a `right` value."""

    @guppy.custom(EitherTestCompiler(0))
    @no_type_check
    def is_left(self: "Either[L, R]") -> bool:
        """Returns `True` for a `left` value."""

    @guppy.custom(EitherTestCompiler(1))
    @no_type_check
    def is_right(self: "Either[L, R]") -> bool:
        """Returns `True` for a `right` value."""

    @guppy.custom(EitherToOptionCompiler(0))
    @no_type_check
    def try_into_left(self: "Either[L, Droppable]" @ owned) -> Option[L]:
        """Returns the wrapped value if `self` is a `left` value, or `nothing`
        otherwise.

        This operation is only allowed if the `right` variant wraps a droppable type.
        """

    @guppy.custom(EitherToOptionCompiler(1))
    @no_type_check
    def try_into_right(self: "Either[Droppable, R]" @ owned) -> Option[R]:
        """Returns the wrapped value if `self` is a `right` value, or `nothing`
        otherwise.

        This operation is only allowed if the `left` variant wraps a droppable type.
        """

    @guppy.custom(EitherUnwrapCompiler(0))
    @no_type_check
    def unwrap_left(self: "Either[L, R]" @ owned) -> L:
        """Returns the contained `left` value, consuming `self`.

        Panics if `self` is a `right` value.
        """

    @guppy.custom(EitherUnwrapCompiler(1))
    @no_type_check
    def unwrap_right(self: "Either[L, R]" @ owned) -> R:
        """Returns the contained `right` value, consuming `self`.

        Panics if `self` is a `left` value.
        """


@guppy.custom(EitherConstructor(0))
@no_type_check
def left(val: L @ owned) -> Either[L, R]:
    """Constructs a `left` either value."""


@guppy.custom(EitherConstructor(1))
@no_type_check
def right(val: R @ owned) -> Either[L, R]:
    """Constructs a `right` either value."""
