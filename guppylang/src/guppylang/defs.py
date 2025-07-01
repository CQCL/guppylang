"""Definition objects that are being exposed to users.

These are the objects returned by the `@guppy` decorator. They should not be confused
with the compiler-internal definition objects in the `definitions` module.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, ClassVar, Generic, ParamSpec, TypeVar, cast

import guppylang_internals
from guppylang_internals.definition.function import CheckedFunctionDef
from guppylang_internals.definition.value import CompiledCallableDef
from guppylang_internals.diagnostic import Error
from guppylang_internals.engine import ENGINE, CoreMetadataKeys
from guppylang_internals.error import GuppyError
from guppylang_internals.span import Span, to_span
from guppylang_internals.tracing.object import TracingDefMixin
from guppylang_internals.tracing.util import hide_trace
from hugr.hugr import Hugr
from hugr.package import Package

import guppylang
from guppylang.emulator import EmulatorBuilder, EmulatorInstance

__all__ = ("GuppyDefinition", "GuppyFunctionDefinition", "GuppyTypeVarDefinition")


P = ParamSpec("P")
Out = TypeVar("Out")


def _update_generator_metadata(hugr: Hugr[Any]) -> None:
    """Update the generator metadata of a Hugr to be
    guppylang rather than just internals."""
    key = CoreMetadataKeys.GENERATOR.value

    hugr.module_root.metadata[key] = {
        "name": f"guppylang (guppylang-internals-v{guppylang_internals.__version__})",
        "version": guppylang.__version__,
    }


@dataclass(frozen=True)
class EntrypointArgsError(Error):
    title: ClassVar[str] = "Entrypoint function has arguments"
    span_label: ClassVar[str] = "Entrypoint function has arguments: {input_names}."
    args: Sequence[str]

    @property
    def input_names(self) -> str:
        """Returns a comma-separated list of input names."""
        return ", ".join(f"`{x}`" for x in self.args)


@dataclass(frozen=True)
class GuppyDefinition(TracingDefMixin):
    """A general Guppy definition."""

    def compile(self, *, entrypoint: bool = True) -> Package:
        """Compile a Guppy definition to HUGR."""
        package: Package = ENGINE.compile(self.id).package
        for mod in package.modules:
            _update_generator_metadata(mod)
        return package

    def check(self) -> None:
        """Type-check a Guppy definition."""
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

        See :py:mod:`guppylang.emulator` for more details on the emulator.


        Args:
            n_qubits: The number of qubits to allocate for the function.
            builder: An optional `EmulatorBuilder` to use for building the emulator
            instance. If not provided, the default `EmulatorBuilder` will be used.

        Returns:
            An `EmulatorInstance` that can be used to run the function in an emulator.
        """
        mod = self.compile(entrypoint=True)

        builder = builder or EmulatorBuilder()
        return builder.build(mod, n_qubits=n_qubits)

    def compile(self, *, entrypoint: bool = True) -> Package:
        """
        Compiles a function definition to a HUGR package.

        If `entrypoint` is True, checks that the entrypoint does not have any arguments.

        Args:
            entrypoint (bool, optional): Whether to treat this definition
              as the entrypoint. Defaults to True.

        Returns:
            Package: The compiled package object.
        Raises:
            GuppyError: If the entrypoint has arguments.
        """

        pack = super().compile(entrypoint=entrypoint)
        # entrypoint cannot be polymorphic
        monomorphized_id = (self.id, ())
        compiled_def = ENGINE.compiled.get(monomorphized_id)
        if (
            entrypoint
            and isinstance(compiled_def, CompiledCallableDef)
            and len(compiled_def.ty.inputs) > 0
        ):
            # Check if the entrypoint being has arguments
            checked = cast(CheckedFunctionDef, ENGINE.checked[self.id])
            start = to_span(checked.defined_at.args.args[0])
            end = to_span(checked.defined_at.args.args[-1])
            span = Span(start=start.start, end=end.end)
            raise GuppyError(
                EntrypointArgsError(
                    span=span,
                    args=compiled_def.ty.input_names or "",
                )
            )
        return pack


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
