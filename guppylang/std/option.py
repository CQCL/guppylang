from pathlib import Path
from typing import Generic, no_type_check

from guppylang.decorator import ModuleIdentifier, guppy
from guppylang.std import builtins
from guppylang.std._internal.compiler.option import (
    OptionConstructor,
    OptionTestCompiler,
    OptionUnwrapCompiler,
    OptionUnwrapNothingCompiler,
)
from guppylang.std.builtins import L, mem_swap, owned
from guppylang.tys.builtin import option_type_def

builtins_module = guppy.get_module(
    ModuleIdentifier(Path(builtins.__file__), "builtins", builtins)
)


@guppy.extend_type(option_type_def, module=builtins_module)
class Option(Generic[L]):  # type: ignore[misc]
    """Represents an optional value."""

    @guppy.custom(OptionTestCompiler(0), module=builtins_module)
    @no_type_check
    def is_nothing(self: "Option[L]") -> bool:
        """Returns `True` if the option is a `nothing` value."""

    @guppy.custom(OptionTestCompiler(1), module=builtins_module)
    @no_type_check
    def is_some(self: "Option[L]") -> bool:
        """Returns `True` if the option is a `some` value."""

    @guppy.custom(OptionUnwrapCompiler(), module=builtins_module)
    @no_type_check
    def unwrap(self: "Option[L]" @ owned) -> L:
        """Returns the contained `some` value, consuming `self`.

        Panics if the option is a `nothing` value.
        """

    @guppy.custom(OptionUnwrapNothingCompiler(), module=builtins_module)
    @no_type_check
    def unwrap_nothing(self: "Option[L]" @ owned) -> None:
        """Returns `None` if the option is a `nothing` value, consuming `self`.

        Panics if the option is a `some` value.
        """

    @guppy(builtins_module)
    @no_type_check
    def take(self: "Option[L]") -> "Option[L]":
        """Swaps the value of `self` with `nothing` and returns the original value."""
        n: Option[L] = nothing()  # type: ignore[type-arg, valid-type]
        mem_swap(n, self)
        return n


@guppy.custom(OptionConstructor(0), module=builtins_module)
@no_type_check
def nothing() -> Option[L]:
    """Constructs a `nothing` optional value."""


@guppy.custom(OptionConstructor(1), module=builtins_module)
@no_type_check
def some(value: L @ owned) -> Option[L]:
    """Constructs a `some` optional value."""
