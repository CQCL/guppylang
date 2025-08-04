"""Definition objects that are being exposed to users.

These are the objects returned by the `@guppy` decorator. They should not be confused
with the compiler-internal definition objects in the `definitions` module.
"""

from dataclasses import dataclass
from typing import Any, ClassVar, Generic, ParamSpec, TypeVar, cast

from hugr.package import Package

from guppylang.engine import ENGINE
from guppylang.tracing.object import TracingDefMixin
from guppylang.tracing.util import hide_trace

from .emulator import EmulatorBuilder, EmulatorInstance

P = ParamSpec("P")
Out = TypeVar("Out")


@dataclass(frozen=True)
class GuppyDefinition(TracingDefMixin):
    """A general Guppy definition."""

    def compile(self) -> Package:
        """Compile a Guppy definition to HUGR."""
        return ENGINE.compile(self.id).package

    def check(self) -> None:
        """Type-check a Guppy definition."""
        from guppylang.engine import ENGINE

        return ENGINE.check(self.id)


@dataclass(frozen=True)
class GuppyFunctionDefinition(GuppyDefinition, Generic[P, Out]):
    """A Guppy function definition."""

    @hide_trace
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Out:
        return cast(Out, super().__call__(*args, **kwargs))

    def emulator(
        self, n_qubits: int, builder: EmulatorBuilder | None = None
    ) -> EmulatorInstance:
        """Compile this function for emulation with the selene-sim emulator.

        Calls `compile()` to get the HUGR package and then builds it using the
        provided `EmulatorBuilder` configuration or a default one.


        Args:
            n_qubits: The number of qubits to allocate for the function.
            builder: An optional `EmulatorBuilder` to use for building the emulator
                instance. If not provided, the default `EmulatorBuilder` will be used.

        Returns:
            An `EmulatorInstance` that can be used to run the function in an emulator.
        """
        mod = self.compile()

        builder = builder or EmulatorBuilder()
        return builder.build(mod, n_qubits=n_qubits)


@dataclass(frozen=True)
class GuppyTypeVarDefinition(GuppyDefinition):
    """Definition of a Guppy type variable."""

    # For type variables, we need a `GuppyDefinition` subclass that answers 'yes' to an
    # instance check on `typing.TypeVar`. This hack is needed since `typing.Generic[T]`
    # has a runtime check that enforces that the passed `T` is actually a `TypeVar`.

    __class__: ClassVar[type] = TypeVar

    _ty_var: TypeVar

    def __eq__(self, other: object) -> bool:
        # We need to compare as equal to an equivalent regular type var
        if isinstance(other, TypeVar):
            return self._ty_var == other
        return object.__eq__(self, other)

    def __getattr__(self, name: str) -> Any:
        # Pretend to be a `TypeVar` by providing all of its attributes
        if hasattr(self._ty_var, name):
            return getattr(self._ty_var, name)
        return object.__getattribute__(self, name)
