from typing import Generic, no_type_check

from guppylang.decorator import guppy
from guppylang.std._internal.compiler.option import (
    OptionConstructor,
    OptionTestCompiler,
    OptionUnwrapCompiler,
    OptionUnwrapNothingCompiler,
)
from guppylang.std.lang import owned
from guppylang.std.mem import mem_swap
from guppylang.tys.builtin import option_type_def

L = guppy.type_var("T", copyable=False, droppable=False)


@guppy.extend_type(option_type_def)
class Option(Generic[L]):  # type: ignore[misc]
    """Represents an optional value."""

    @guppy.custom(OptionTestCompiler(0))
    @no_type_check
    def is_nothing(self: "Option[L]") -> bool:
        """Returns `True` if the option is a `nothing` value."""

    @guppy.custom(OptionTestCompiler(1))
    @no_type_check
    def is_some(self: "Option[L]") -> bool:
        """Returns `True` if the option is a `some` value."""

    @guppy.custom(OptionUnwrapCompiler())
    @no_type_check
    def unwrap(self: "Option[L]" @ owned) -> L:
        """Returns the contained `some` value, consuming `self`.

        Panics if the option is a `nothing` value.
        """

    @guppy.custom(OptionUnwrapNothingCompiler())
    @no_type_check
    def unwrap_nothing(self: "Option[L]" @ owned) -> None:
        """Returns `None` if the option is a `nothing` value, consuming `self`.

        Panics if the option is a `some` value.
        """

    @guppy
    @no_type_check
    def swap(self: "Option[L]", other: "Option[L]" @ owned) -> "Option[L]":
        """Swaps the value of `self` with `other` and returns the original value."""
        mem_swap(self, other)
        return other

    @guppy
    @no_type_check
    def take(self: "Option[L]") -> "Option[L]":
        """Swaps the value of `self` with `nothing` and returns the original value."""
        return self.swap(nothing())


@guppy.custom(OptionConstructor(0))
@no_type_check
def nothing() -> Option[L]:
    """Constructs a `nothing` optional value."""


@guppy.custom(OptionConstructor(1))
@no_type_check
def some(value: L @ owned) -> Option[L]:
    """Constructs a `some` optional value."""
