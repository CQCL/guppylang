from collections.abc import Sequence
from typing import Generic, no_type_check

import hugr.tys as ht

from guppylang.decorator import guppy
from guppylang.error import InternalGuppyError
from guppylang.std._internal.compiler.option import (
    OptionConstructor,
    OptionTestCompiler,
    OptionUnwrapCompiler,
)
from guppylang.std.builtins import owned
from guppylang.tys.arg import Argument, TypeArg
from guppylang.tys.param import TypeParam


def _option_to_hugr(args: Sequence[Argument]) -> ht.Type:
    match args:
        case [TypeArg(ty)]:
            return ht.Option(ty.to_hugr())
        case _:
            raise InternalGuppyError("Invalid type args for Option")


T = guppy.type_var("T", copyable=False, droppable=False)


@guppy.type(
    _option_to_hugr,
    params=[TypeParam(0, "T", must_be_copyable=False, must_be_droppable=False)],
)
class Option(Generic[T]):  # type: ignore[misc]
    """Represents an optional value."""

    @guppy.custom(OptionTestCompiler(0))
    @no_type_check
    def is_nothing(self: "Option[T]") -> bool:
        """Returns `True` if the option is a `nothing` value."""

    @guppy.custom(OptionTestCompiler(1))
    @no_type_check
    def is_some(self: "Option[T]") -> bool:
        """Returns `True` if the option is a `some` value."""

    @guppy.custom(OptionUnwrapCompiler())
    @no_type_check
    def unwrap(self: "Option[T]" @ owned) -> T:
        """Returns the contained `some` value, consuming `self`.

        Panics if the option is a `nothing` value.
        """


@guppy.custom(OptionConstructor(0))
@no_type_check
def nothing() -> Option[T]:
    """Constructs a `nothing` optional value."""


@guppy.custom(OptionConstructor(1))
@no_type_check
def some(value: T @ owned) -> Option[T]:
    """Constructs a `some` optional value."""
