"""Definition objects that are being exposed to users.

These are the objects returned by the `@guppy` decorator. They should not be confused
with the compiler-internal definition objects in the `definitions` module.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Generic, ParamSpec, TypeVar, cast

from hugr.package import Package

from guppylang.definition.common import MonomorphizableDef
from guppylang.engine import ENGINE
from guppylang.tracing.object import TracingDefMixin
from guppylang.tracing.util import hide_trace

from .emulator import EmulatorBuilder, EmulatorInstance

if TYPE_CHECKING:
    from guppylang.compiler.core import PartiallyMonomorphizedArgs

P = ParamSpec("P")
Out = TypeVar("Out")


@dataclass(frozen=True)
class GuppyDefinition(TracingDefMixin):
    """A general Guppy definition."""

    def compile(self) -> Package:
        """Compile a Guppy definition to HUGR."""
        return ENGINE.compile(self.id).package

    def check(self) -> None:
        """Type check a Guppy definition."""
        from guppylang.engine import ENGINE

        return ENGINE.check(self.id)


@dataclass(frozen=True)
class GuppyFunctionDefinition(GuppyDefinition, Generic[P, Out]):
    """A Guppy function definition."""

    @hide_trace
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Out:
        return cast(Out, super().__call__(*args, **kwargs))

    def compile(self) -> Package:
        """Compile a Guppy function definition to HUGR."""
        compiled_module = ENGINE.compile(self.id)

        # Look up how many generic params the function has so we can create an empty
        # partial monomorphization to look up in the context
        checked_def = ENGINE.checked[self.id]
        mono_args: PartiallyMonomorphizedArgs | None = None
        if isinstance(checked_def, MonomorphizableDef):
            mono_args = tuple(None for _ in checked_def.params)

        _ = ENGINE.compiled[self.id, mono_args]
        return compiled_module.package

    def emulator(self, builder: EmulatorBuilder | None = None) -> EmulatorInstance:
        mod = self.compile()

        builder = builder or EmulatorBuilder()
        return builder.build(mod)


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
