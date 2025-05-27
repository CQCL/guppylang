import functools
import inspect
import itertools
from collections.abc import Callable, Iterator, Sequence
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, NamedTuple, TypeAlias, TypeVar

from hugr import Wire

import guppylang.checker.expr_checker as expr_checker
from guppylang.checker.errors.generic import UnsupportedError
from guppylang.checker.errors.type_errors import (
    BinaryOperatorNotDefinedError,
    UnaryOperatorNotDefinedError,
)
from guppylang.definition.common import DefId, Definition
from guppylang.definition.ty import TypeDef
from guppylang.definition.value import (
    CallableDef,
    CompiledCallableDef,
    CompiledValueDef,
)
from guppylang.engine import DEF_STORE, ENGINE
from guppylang.error import GuppyComptimeError, GuppyError, GuppyTypeError
from guppylang.ipython_inspect import find_ipython_def, is_running_ipython
from guppylang.tracing.state import get_tracing_state, tracing_active
from guppylang.tracing.util import capture_guppy_errors, get_calling_frame, hide_trace
from guppylang.tys.ty import FunctionType, StructType, Type

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

    Emits a user error if the unary operation is not defined for the given type.
    """

    @functools.wraps(f)
    @capture_guppy_errors
    def wrapped(self: "DunderMixin") -> Any:
        from guppylang.tracing.state import get_tracing_state
        from guppylang.tracing.unpacking import guppy_object_from_py

        state = get_tracing_state()
        self = guppy_object_from_py(self, state.dfg.builder, state.node)

        with suppress(Exception):
            return f(self)

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
        from guppylang.tracing.state import get_tracing_state
        from guppylang.tracing.unpacking import guppy_object_from_py

        state = get_tracing_state()
        self = guppy_object_from_py(self, state.dfg.builder, state.node)
        other = guppy_object_from_py(other, state.dfg.builder, state.node)

        # First try the method on `self`
        with suppress(Exception):
            return f(self, other)

        # If that failed, try the reverse method on `other`.
        # NB: We know that `f.__name__` is in one of the tables since we make sure to
        # only put this decorator on the correct dunder methods below
        if f.__name__ in binary_table:
            reverse_method, display_name = binary_table[f.__name__]
            left_ty, right_ty = self._ty, other._ty
        else:
            reverse_method, display_name = reverse_binary_table[f.__name__]
            left_ty, right_ty = other._ty, self._ty
        with suppress(Exception):
            return other.__getattr__(reverse_method)(self)

        raise GuppyTypeError(
            BinaryOperatorNotDefinedError(state.node, left_ty, right_ty, display_name)
        )

    return wrapped


class DunderMixin:
    """Mixin class to allow `GuppyObject`s and `GuppyDefinition`s to be used in
    arithmetic expressions etc. via providing the corresponding dunder methods
    delegating to the objects impls.
    """

    def _get_method(self, name: str) -> Any:
        from guppylang.tracing.state import get_tracing_state
        from guppylang.tracing.unpacking import guppy_object_from_py

        state = get_tracing_state()
        self = guppy_object_from_py(self, state.dfg.builder, state.node)
        return self.__getattr__(name)

    def __abs__(self) -> Any:
        return self._get_method("__abs__")()

    @binary_operation
    def __add__(self, other: Any) -> Any:
        return self._get_method("__add__")(other)

    @binary_operation
    def __and__(self, other: Any) -> Any:
        return self._get_method("__and__")(other)

    def __bool__(self: Any) -> Any:
        return self._get_method("__bool__")()

    def __ceil__(self: Any) -> Any:
        return self._get_method("__ceil__")()

    def __divmod__(self, other: Any) -> Any:
        return self._get_method("__divmod__")(other)

    @binary_operation
    def __eq__(self, other: object) -> Any:
        return self._get_method("__eq__")(other)

    def __float__(self) -> Any:
        return self._get_method("__float__")()

    def __floor__(self) -> Any:
        return self._get_method("__floor__")()

    @binary_operation
    def __floordiv__(self, other: Any) -> Any:
        return self._get_method("__floordiv__")(other)

    @binary_operation
    def __ge__(self, other: Any) -> Any:
        return self._get_method("__ge__")(other)

    @binary_operation
    def __gt__(self, other: Any) -> Any:
        return self._get_method("__gt__")(other)

    def __int__(self) -> Any:
        return self._get_method("__int__")()

    @unary_operation
    def __invert__(self) -> Any:
        return self._get_method("__invert__")()

    @binary_operation
    def __le__(self, other: Any) -> Any:
        return self._get_method("__le__")(other)

    @binary_operation
    def __lshift__(self, other: Any) -> Any:
        return self._get_method("__lshift__")(other)

    @binary_operation
    def __lt__(self, other: Any) -> Any:
        return self._get_method("__lt__")(other)

    @binary_operation
    def __mod__(self, other: Any) -> Any:
        return self._get_method("__mod__")(other)

    @binary_operation
    def __mul__(self, other: Any) -> Any:
        return self._get_method("__mul__")(other)

    @binary_operation
    def __ne__(self, other: object) -> Any:
        return self._get_method("__ne__")(other)

    @unary_operation
    def __neg__(self) -> Any:
        return self._get_method("__neg__")()

    @binary_operation
    def __or__(self, other: Any) -> Any:
        return self._get_method("__or__")(other)

    @unary_operation
    def __pos__(self) -> Any:
        return self._get_method("__pos__")()

    @binary_operation
    def __pow__(self, other: Any) -> Any:
        return self._get_method("__pow__")(other)

    @binary_operation
    def __radd__(self, other: Any) -> Any:
        return self._get_method("__radd__")(other)

    @binary_operation
    def __rand__(self, other: Any) -> Any:
        return self._get_method("__rand__")(other)

    @binary_operation
    def __rfloordiv__(self, other: Any) -> Any:
        return self._get_method("__rfloordiv__")(other)

    @binary_operation
    def __rlshift__(self, other: Any) -> Any:
        return self._get_method("__rlshift__")(other)

    @binary_operation
    def __rmod__(self, other: Any) -> Any:
        return self._get_method("__rmod__")(other)

    @binary_operation
    def __rmul__(self, other: Any) -> Any:
        return self._get_method("__rmul__")(other)

    @binary_operation
    def __ror__(self, other: Any) -> Any:
        return self._get_method("__ror__")(other)

    @binary_operation
    def __rpow__(self, other: Any) -> Any:
        return self._get_method("__rpow__")(other)

    @binary_operation
    def __rrshift__(self, other: Any) -> Any:
        return self._get_method("__pow__")(other)

    @binary_operation
    def __rshift__(self, other: Any) -> Any:
        return self._get_method("__rshift__")(other)

    @binary_operation
    def __rsub__(self, other: Any) -> Any:
        return self._get_method("__rsub__")(other)

    @binary_operation
    def __rtruediv__(self, other: Any) -> Any:
        return self._get_method("__rtruediv__")(other)

    @binary_operation
    def __rxor__(self, other: Any) -> Any:
        return self._get_method("__rxor__")(other)

    @binary_operation
    def __sub__(self, other: Any) -> Any:
        return self._get_method("__sub__")(other)

    @binary_operation
    def __truediv__(self, other: Any) -> Any:
        return self._get_method("__truediv__")(other)

    def __trunc__(self) -> Any:
        return self._get_method("__trunc__")()

    @binary_operation
    def __xor__(self, other: Any) -> Any:
        return self._get_method("__xor__")(other)


class ObjectUse(NamedTuple):
    """Records a use of a non-copyable `GuppyObject`."""

    #: Path of the Python file in which the use occurred
    module: str

    #: Line number of the use
    lineno: int

    #: If the use was as an argument to a Guppy function, we also record a reference to
    #: the called function.
    called_func: CompiledCallableDef | None


@dataclass(frozen=True)
class GuppyObjectId:
    """Unique id for abstract GuppyObjects allocated during tracing."""

    id: int

    _fresh_ids: ClassVar[Iterator[int]] = itertools.count()

    @classmethod
    def fresh(cls) -> "GuppyObjectId":
        return GuppyObjectId(next(cls._fresh_ids))


class GuppyObject(DunderMixin):
    """The runtime representation of abstract Guppy objects during tracing.

    They correspond to a single Hugr wire within the current dataflow graph.
    """

    #: The type of this object
    _ty: Type

    #: The Hugr wire holding this object
    _wire: Wire

    #: Whether this object has been used
    _used: ObjectUse | None

    #: Unique id for this object
    _id: GuppyObjectId

    def __init__(self, ty: Type, wire: Wire, used: ObjectUse | None = None) -> None:
        self._ty = ty
        self._wire = wire
        self._used = used
        self._id = GuppyObjectId.fresh()
        state = get_tracing_state()
        if not ty.droppable and not self._used:
            state.unused_undroppable_objs[self._id] = self

    @hide_trace
    def __getattr__(self, key: str) -> Any:  # type: ignore[misc]
        # Guppy objects don't have fields (structs are treated separately below), so the
        # only attributes we have to worry about are methods.
        func = get_tracing_state().globals.get_instance_func(self._ty, key)
        if func is None:
            raise GuppyComptimeError(
                f"Expression of type `{self._ty}` has no attribute `{key}`"
            )
        return lambda *xs: GuppyDefinition(func)(self, *xs)

    @hide_trace
    def __bool__(self) -> Any:
        err = (
            "Can't branch on a dynamic Guppy value since its concrete value is not "
            "known at comptime. Consider defining a regular Guppy function to perform "
            "dynamic branching."
        )
        raise GuppyComptimeError(err)

    @hide_trace
    @capture_guppy_errors
    def __call__(self, *args: Any) -> Any:
        if not isinstance(self._ty, FunctionType):
            err = f"Value of type `{self._ty}` is not callable"
            raise GuppyComptimeError(err)

        # TODO: Support higher-order functions
        state = get_tracing_state()
        raise GuppyError(
            UnsupportedError(state.node, "Higher-order comptime functions")
        )

    @hide_trace
    def __iter__(self) -> Any:
        # Abstract Guppy objects are not iterable from Python since our iterator
        # protocol doesn't work during tracing.
        raise GuppyComptimeError(
            f"Expression of type `{self._ty}` is not iterable at comptime"
        )

    def _use_wire(self, called_func: CompiledCallableDef | None) -> Wire:
        # Panic if the value has already been used
        if self._used and not self._ty.copyable:
            use = self._used
            # TODO: Should we print the full path to the file or only the name as is
            #  done here? Note that the former will lead to challenges with golden
            #  tests
            filename = Path(use.module).name
            err = (
                f"Value with non-copyable type `{self._ty}` was already used\n\n"
                f"Previous use occurred in {filename}:{use.lineno}"
            )
            if use.called_func:
                err += f" as an argument to `{use.called_func.name}`"
            raise GuppyComptimeError(err)
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
            if not self._ty.droppable:
                state = get_tracing_state()
                state.unused_undroppable_objs.pop(self._id)
        return self._wire


class GuppyStructObject(DunderMixin):
    """The runtime representation of Guppy struct objects during tracing.

    Note that `GuppyStructObject` is not a `GuppyObject` itself since it's not backed
    by a single wire, but it can contain multiple of them.

    Mutation of structs during tracing is generally unchecked. We allow users to write
    whatever they want into the fields, making it more or less isomorphic to a Python
    dataclass. Thus, structs need to be checked at function call boundaries to ensure
    that the user hasn't messed up. This is done in `guppylang.tracing.unpacking.
    guppy_object_from_py`.

    Similar to dataclasses, we allow structs to be `frozen` which makes them immutable.
    This is needed to preserve Python semantics when structs are used as non-borrowed
    function arguments: Mutation in the function body cannot be observed from the
    outside, so we prevent it to avoid confusion.
    """

    #: The type of this struct object
    _ty: StructType

    #: Mapping from field names to values. The values can be any Python object.
    _field_values: dict[str, Any]

    #: Whether this struct object is frozen, i.e. immutable
    _frozen: bool

    def __init__(
        self, ty: StructType, field_values: Sequence[Any], frozen: bool
    ) -> None:
        field_values_dict = {
            f.name: v for f, v in zip(ty.fields, field_values, strict=True)
        }
        # Can't use regular assignment for class attributes since we override
        # `__setattr__` below
        object.__setattr__(self, "_ty", ty)
        object.__setattr__(self, "_field_values", field_values_dict)
        object.__setattr__(self, "_frozen", frozen)

    @hide_trace
    def __getattr__(self, key: str) -> Any:  # type: ignore[misc]
        # It could be an attribute
        if key in self._field_values:
            return self._field_values[key]
        # Or a method
        func = get_tracing_state().globals.get_instance_func(self._ty, key)
        if func is None:
            err = f"Expression of type `{self._ty}` has no attribute `{key}`"
            raise AttributeError(err)
        return lambda *xs: GuppyDefinition(func)(self, *xs)

    @hide_trace
    def __setattr__(self, key: str, value: Any) -> None:
        if key in self._field_values:
            if self._frozen:
                err = (
                    f"Object of type `{self._ty}` is an owned function argument. "
                    "Therefore, this mutation won't be visible to the caller."
                )
                raise GuppyComptimeError(err)
            self._field_values[key] = value
        else:
            err = f"Expression of type `{self._ty}` has no attribute `{key}`"
            raise AttributeError(err)

    @hide_trace
    def __iter__(self) -> Any:
        # Abstract Guppy objects are not iterable from Python since our iterator
        # protocol doesn't work during tracing.
        raise GuppyComptimeError(f"Expression of type `{self._ty}` is not iterable")


@dataclass(frozen=True)
class GuppyDefinition(DunderMixin):
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

        if not tracing_active():
            raise GuppyComptimeError(
                f"{self.wrapped.description.capitalize()} `{self.wrapped.name}` may "
                "only be called in a Guppy context"
            )

        state = get_tracing_state()
        defn = ENGINE.get_checked(self.wrapped.id)
        defn = state.ctx.build_compiled_def(defn.id)
        if isinstance(defn, CompiledCallableDef):
            return trace_call(defn, *args)
        elif (
            isinstance(defn, TypeDef)
            and defn.id in DEF_STORE.impls
            and "__new__" in DEF_STORE.impls[defn.id]
        ):
            constructor = DEF_STORE.raw_defs[DEF_STORE.impls[defn.id]["__new__"]]
            return GuppyDefinition(constructor)(*args)
        err = f"{defn.description.capitalize()} `{defn.name}` is not callable"
        raise GuppyComptimeError(err)

    def __getitem__(self, item: Any) -> Any:
        # If this is a type definition, then `__getitem__` might be called when
        # specifying generic arguments
        if isinstance(self.wrapped, TypeDef):
            # It doesn't really matter what we return here since we don't support types
            # as comptime values yet, so just give back the definition
            return self
        # TODO: Alternatively, it could be a type application on a generic function.
        #  Supporting those requires a comptime representation of types as values
        if tracing_active():
            state = get_tracing_state()
            defn = state.globals[self.wrapped.id]
            if isinstance(defn, CallableDef) and defn.ty.parametrized:
                raise GuppyComptimeError(
                    "Explicitly specifying type arguments of generic functions in a "
                    "comptime context is not supported yet"
                )
        raise GuppyComptimeError(
            f"{self.wrapped.description.capitalize()} `{self.wrapped.name}` is not "
            "subscriptable"
        )

    def to_guppy_object(self) -> GuppyObject:
        state = get_tracing_state()
        defn = state.ctx.build_compiled_def(self.id)
        if isinstance(defn, CompiledValueDef):
            wire = defn.load(state.dfg, state.ctx, state.node)
            return GuppyObject(defn.ty, wire, None)
        elif isinstance(defn, TypeDef):
            if defn.id in DEF_STORE.impls and "__new__" in DEF_STORE.impls[defn.id]:
                constructor = DEF_STORE.raw_defs[DEF_STORE.impls[defn.id]["__new__"]]
                return GuppyDefinition(constructor).to_guppy_object()
        err = f"{defn.description.capitalize()} `{defn.name}` is not a value"
        raise GuppyComptimeError(err)

    def compile(self) -> Any:
        from guppylang.engine import ENGINE

        return ENGINE.compile(self.id)


class TypeVarGuppyDefinition(  # type: ignore[misc, call-arg]
    GuppyDefinition,
    TypeVar,
    # TypeVar inherits from `typing._Final` so we need to pretend to be the root
    # definition in order to subclass it
    _root=True,
):
    """A `GuppyDefinition` subclass that is also a subclass of `TypeVar`.

    This is the object returned by `guppy.type_var`. The `TypeVar` inheritance is needed
    since `typing.Generic[T]` has a runtime check that enforces that the passed `T` is
    actually a `TypeVar`.
    """
