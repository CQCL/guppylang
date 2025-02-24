import functools
import inspect
import itertools
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NamedTuple, TypeAlias

from hugr import Wire, ops

import guppylang.checker.expr_checker as expr_checker
from guppylang.checker.errors.generic import UnsupportedError
from guppylang.checker.errors.type_errors import (
    BinaryOperatorNotDefinedError,
    UnaryOperatorNotDefinedError,
)
from guppylang.definition.common import DefId, Definition
from guppylang.definition.function import RawFunctionDef
from guppylang.definition.ty import TypeDef
from guppylang.definition.value import CompiledCallableDef, CompiledValueDef
from guppylang.error import GuppyError, GuppyTypeError
from guppylang.ipython_inspect import find_ipython_def, is_running_ipython
from guppylang.tracing.state import get_tracing_globals, get_tracing_state
from guppylang.tracing.util import capture_guppy_errors, get_calling_frame, hide_trace
from guppylang.tys.ty import FunctionType, StructType, TupleType, Type

# Mapping from unary dunder method to display name of the operation
unary_table = dict(expr_checker.unary_table.values())

# Mapping from binary dunder method to reversed method and display name of the operation
binary_table = {
    method: (reverse_method, display_name)
    for method, reverse_method, display_name in expr_checker.binary_table.values()
}

# Mapping from reverse binary dunder method to original method and display name of the
# operation
reverse_binary_table = {
    reverse_method: (method, display_name)
    for method, reverse_method, display_name in expr_checker.binary_table.values()
}

UnaryDunderMethod: TypeAlias = Callable[["DunderMixin"], Any]
BinaryDunderMethod: TypeAlias = Callable[["DunderMixin", Any], Any]


def unary_operation(f: UnaryDunderMethod) -> UnaryDunderMethod:
    """Decorator for methods corresponding to unary operations like `__neg__` etc.

    Emits a user error if the binary operation is not defined for the given type.
    """

    @functools.wraps(f)
    @capture_guppy_errors
    def wrapped(self: "DunderMixin") -> Any:
        with suppress(Exception):
            return f(self)

        from guppylang.tracing.state import get_tracing_state

        state = get_tracing_state()
        assert isinstance(self, GuppyObject)
        raise GuppyTypeError(
            UnaryOperatorNotDefinedError(state.node, self._ty, unary_table[f.__name__])
        )

    return wrapped


def binary_operation(f: BinaryDunderMethod) -> BinaryDunderMethod:
    """Decorator for methods corresponding to binary operations like `__add__` etc.

    Delegate calls to their reversed versions `__radd__` etc. if the original one
    doesn't type check. Otherwise, emits an error informing the user that the binary
    operation is not defined for those types.
    """

    @functools.wraps(f)
    @capture_guppy_errors
    def wrapped(self: "DunderMixin", other: Any) -> Any:
        with suppress(Exception):
            return f(self, other)
        with suppress(Exception):
            from guppylang.tracing.state import get_tracing_state
            from guppylang.tracing.unpacking import guppy_object_from_py

            state = get_tracing_state()
            obj = guppy_object_from_py(other, state.dfg.builder, state.node)

            if f.__name__ in binary_table:
                reverse_method, display_name = binary_table[f.__name__]
                left_ty, right_ty = self._ty, obj._ty
            else:
                reverse_method, display_name = reverse_binary_table[f.__name__]
                left_ty, right_ty = obj._ty, self._ty
            return obj.__getattr__(reverse_method)(self)

        assert isinstance(self, GuppyObject)
        raise GuppyTypeError(
            BinaryOperatorNotDefinedError(state.node, left_ty, right_ty, display_name)
        )

    return wrapped


class DunderMixin(ABC):
    """Mixin class to allow `GuppyObject`s to be used in arithmetic expressions etc.
    via providing the corresponding dunder methods delegating to the objects impls.
    """

    @abstractmethod
    def __getattr__(self, item: Any) -> Any: ...

    def __abs__(self) -> Any:
        return self.__getattr__("__abs__")()

    @binary_operation
    def __add__(self, other: Any) -> Any:
        return self.__getattr__("__add__")(other)

    @binary_operation
    def __and__(self, other: Any) -> Any:
        return self.__getattr__("__and__")(other)

    def __bool__(self: Any) -> Any:
        return self.__getattr__("__bool__")()

    def __ceil__(self: Any) -> Any:
        return self.__getattr__("__ceil__")()

    def __divmod__(self, other: Any) -> Any:
        return self.__getattr__("__divmod__")(other)

    @binary_operation
    def __eq__(self, other: object) -> Any:
        return self.__getattr__("__eq__")(other)

    def __float__(self) -> Any:
        return self.__getattr__("__float__")()

    def __floor__(self) -> Any:
        return self.__getattr__("__floor__")()

    @binary_operation
    def __floordiv__(self, other: Any) -> Any:
        return self.__getattr__("__floordiv__")(other)

    @binary_operation
    def __ge__(self, other: Any) -> Any:
        return self.__getattr__("__ge__")(other)

    @binary_operation
    def __gt__(self, other: Any) -> Any:
        return self.__getattr__("__gt__")(other)

    def __int__(self) -> Any:
        return self.__getattr__("__int__")()

    @unary_operation
    def __invert__(self) -> Any:
        return self.__getattr__("__invert__")()

    @binary_operation
    def __le__(self, other: Any) -> Any:
        return self.__getattr__("__le__")(other)

    @binary_operation
    def __lshift__(self, other: Any) -> Any:
        return self.__getattr__("__lshift__")(other)

    @binary_operation
    def __lt__(self, other: Any) -> Any:
        return self.__getattr__("__lt__")(other)

    @binary_operation
    def __mod__(self, other: Any) -> Any:
        return self.__getattr__("__mod__")(other)

    @binary_operation
    def __mul__(self, other: Any) -> Any:
        return self.__getattr__("__mul__")(other)

    @binary_operation
    def __ne__(self, other: object) -> Any:
        return self.__getattr__("__ne__")(other)

    @unary_operation
    def __neg__(self) -> Any:
        return self.__getattr__("__neg__")()

    @binary_operation
    def __or__(self, other: Any) -> Any:
        return self.__getattr__("__or__")(other)

    @unary_operation
    def __pos__(self) -> Any:
        return self.__getattr__("__pos__")()

    @binary_operation
    def __pow__(self, other: Any) -> Any:
        return self.__getattr__("__pow__")(other)

    @binary_operation
    def __radd__(self, other: Any) -> Any:
        return self.__getattr__("__radd__")(other)

    @binary_operation
    def __rand__(self, other: Any) -> Any:
        return self.__getattr__("__rand__")(other)

    @binary_operation
    def __rfloordiv__(self, other: Any) -> Any:
        return self.__getattr__("__rfloordiv__")(other)

    @binary_operation
    def __rlshift__(self, other: Any) -> Any:
        return self.__getattr__("__rlshift__")(other)

    @binary_operation
    def __rmod__(self, other: Any) -> Any:
        return self.__getattr__("__rmod__")(other)

    @binary_operation
    def __rmul__(self, other: Any) -> Any:
        return self.__getattr__("__rmul__")(other)

    @binary_operation
    def __ror__(self, other: Any) -> Any:
        return self.__getattr__("__ror__")(other)

    @binary_operation
    def __rpow__(self, other: Any) -> Any:
        return self.__getattr__("__rpow__")(other)

    @binary_operation
    def __rrshift__(self, other: Any) -> Any:
        return self.__getattr__("__pow__")(other)

    @binary_operation
    def __rshift__(self, other: Any) -> Any:
        return self.__getattr__("__rshift__")(other)

    @binary_operation
    def __rsub__(self, other: Any) -> Any:
        return self.__getattr__("__rsub__")(other)

    @binary_operation
    def __rtruediv__(self, other: Any) -> Any:
        return self.__getattr__("__rtruediv__")(other)

    @binary_operation
    def __rxor__(self, other: Any) -> Any:
        return self.__getattr__("__rxor__")(other)

    @binary_operation
    def __sub__(self, other: Any) -> Any:
        return self.__getattr__("__sub__")(other)

    @binary_operation
    def __truediv__(self, other: Any) -> Any:
        return self.__getattr__("__truediv__")(other)

    def __trunc__(self) -> Any:
        return self.__getattr__("__trunc__")()

    @binary_operation
    def __xor__(self, other: Any) -> Any:
        return self.__getattr__("__xor__")(other)


class ObjectUse(NamedTuple):
    """Records a use of a linear `GuppyObject`."""

    module: str
    lineno: int
    called_func: CompiledCallableDef | None


ObjectId = int

fresh_id = itertools.count()


class GuppyObject(DunderMixin):
    """The runtime representation of abstract Guppy objects during tracing."""

    _ty: Type
    _wire: Wire
    _used: ObjectUse | None
    _id: ObjectId

    def __init__(self, ty: Type, wire: Wire, used: ObjectUse | None = None) -> None:
        self._ty = ty
        self._wire = wire
        self._used = used
        self._id = next(fresh_id)
        state = get_tracing_state()
        state.allocated_objs[self._id] = self
        if ty.linear and not self._used:
            state.unused_objs.add(self._id)

    @hide_trace
    def __getattr__(self, key: str) -> Any:  # type: ignore[misc]
        globals = get_tracing_globals()
        func = globals.get_instance_func(self._ty, key)
        if func is None:
            raise AttributeError(
                f"Expression of type `{self._ty}` has no attribute `{key}`"
            )
        return lambda *xs: GuppyDefinition(func)(self, *xs)

    @hide_trace
    def __bool__(self) -> Any:
        err = (
            "Branching on a dynamic value is not allowed during tracing. Try using "
            "a regular guppy function"
        )
        raise ValueError(err)

    @hide_trace
    @capture_guppy_errors
    def __call__(self, *args: Any) -> Any:
        if not isinstance(self._ty, FunctionType):
            err = f"Value of type `{self._ty}` is not callable"
            raise TypeError(err)

        # TODO: Support higher-order functions
        state = get_tracing_state()
        raise GuppyError(
            UnsupportedError(state.node, "Higher-order comptime functions")
        )

    @hide_trace
    def __iter__(self) -> Any:
        state = get_tracing_state()
        builder = state.dfg.builder
        if isinstance(self._ty, TupleType):
            unpack = builder.add_op(ops.UnpackTuple(), self._use_wire(None))
            return (
                GuppyObject(ty, wire)
                for ty, wire in zip(
                    self._ty.element_types, unpack.outputs(), strict=True
                )
            )
        raise TypeError(f"Expression of type `{self._ty}` is not iterable")

    def _use_wire(self, called_func: CompiledCallableDef | None) -> Wire:
        # Panic if the value has already been used
        if self._used and self._ty.linear:
            use = self._used
            # TODO: Should we print the full path to the file or only the name as is
            #  done here? Note that the former will lead to challenges with golden
            #  tests
            filename = Path(use.module).name
            err = (
                f"Value with linear type `{self._ty}` was already used\n\n"
                f"Previous use occurred in {filename}:{use.lineno}"
            )
            if use.called_func:
                err += f" as an argument to `{use.called_func.name}`"
            raise ValueError(err)
        # Otherwise, mark it as used
        else:
            frame = get_calling_frame()
            assert frame is not None
            if is_running_ipython():
                module_name = "<In [?]>"
                if defn := find_ipython_def(frame.f_code.co_name):
                    module_name = f"<{defn.cell_name}>"
            else:
                module = inspect.getmodule(frame)
                module_name = module.__file__ if module and module.__file__ else "???"
            self._used = ObjectUse(module_name, frame.f_lineno, called_func)
            if self._ty.linear:
                state = get_tracing_state()
                state.unused_objs.remove(self._id)
        return self._wire


class GuppyStructObject:
    """The runtime representation of Guppy struct objects during tracing."""

    _ty: StructType
    _field_values: dict[str, Any]
    _frozen: bool

    def __init__(
        self, ty: StructType, field_values: Sequence[Any], frozen: bool
    ) -> None:
        field_values_dict = {
            f.name: v for f, v in zip(ty.fields, field_values, strict=True)
        }
        object.__setattr__(self, "_ty", ty)
        object.__setattr__(self, "_field_values", field_values_dict)
        object.__setattr__(self, "_frozen", frozen)

    @hide_trace
    def __getattr__(self, key: str) -> Any:  # type: ignore[misc]
        # It could be an attribute
        if key in self._field_values:
            return self._field_values[key]
        # Or a method
        globals = get_tracing_globals()
        func = globals.get_instance_func(self._ty, key)
        if func is None:
            err = f"Expression of type `{self._ty}` has no attribute `{key}`"
            raise AttributeError(err)
        return lambda *xs: GuppyDefinition(func)(self, *xs)

    @hide_trace
    def __setattr__(self, key: str, value: Any) -> None:
        if key in self._field_values:
            if self._frozen:
                err = f"Object of type `{self._ty}` is immutable"
                raise TypeError(err)
            self._field_values[key] = value
        else:
            err = f"Expression of type `{self._ty}` has no attribute `{key}`"
            raise AttributeError(err)


@dataclass(frozen=True)
class GuppyDefinition:
    """A top-level Guppy definition.

    This is the object that is returned to the users when they decorate a function or
    class. In particular, this is the version of the definition that is available during
    tracing.
    """

    wrapped: Definition

    @property
    def id(self) -> DefId:
        return self.wrapped.id

    @hide_trace
    def __call__(self, *args: Any) -> Any:
        from guppylang.tracing.function import trace_call

        # Check that the functions is loaded in the current module
        globals = get_tracing_globals()
        if self.wrapped.id not in globals.defs:
            assert self.wrapped.id.module is not None
            err = (
                f"{self.wrapped.description.capitalize()} `{self.wrapped.name}` is not "
                f"available in this module, consider importing it from "
                f"`{self.wrapped.id.module.name}`"
            )
            raise TypeError(err)

        state = get_tracing_state()
        defn = state.ctx.build_compiled_def(self.wrapped.id)
        if isinstance(defn, CompiledCallableDef):
            return trace_call(defn, *args)
        elif (
            isinstance(defn, TypeDef)
            and defn.id in globals.impls
            and "__new__" in globals.impls[defn.id]
        ):
            constructor = globals.defs[globals.impls[defn.id]["__new__"]]
            return GuppyDefinition(constructor)(*args)
        err = f"{defn.description.capitalize()} `{defn.name}` is not callable"
        raise TypeError(err)

    def __getitem__(self, item: Any) -> Any:
        return self

    def to_guppy_object(self) -> GuppyObject:
        state = get_tracing_state()
        defn = state.ctx.build_compiled_def(self.id)
        if isinstance(defn, CompiledValueDef):
            wire = defn.load(state.dfg, state.ctx, state.node)
            return GuppyObject(defn.ty, wire, None)
        elif isinstance(defn, TypeDef):
            globals = get_tracing_globals()
            if defn.id in globals.impls and "__new__" in globals.impls[defn.id]:
                constructor = globals.defs[globals.impls[defn.id]["__new__"]]
                return GuppyDefinition(constructor).to_guppy_object()
        err = f"{defn.description.capitalize()} `{defn.name}` is not a value"
        raise TypeError(err)

    def compile(self) -> Any:
        from guppylang.decorator import guppy

        assert isinstance(self.wrapped, RawFunctionDef)
        return guppy.compile_function(self.wrapped)
