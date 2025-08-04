import inspect
from collections.abc import Callable, Sequence
from types import FrameType
from typing import ParamSpec, TypeVar

from hugr import ops
from hugr import tys as ht

from guppylang.defs import (
    GuppyDefinition,
    GuppyFunctionDefinition,
)
from guppylang_internals.compiler.core import (
    CompilerContext,
)
from guppylang_internals.definition.common import DefId
from guppylang_internals.definition.custom import (
    CustomCallChecker,
    CustomInoutCallCompiler,
    DefaultCallChecker,
    NotImplementedCallCompiler,
    OpCompiler,
    RawCustomFunctionDef,
)
from guppylang_internals.definition.ty import OpaqueTypeDef, TypeDef
from guppylang_internals.engine import DEF_STORE
from guppylang_internals.tys.arg import Argument
from guppylang_internals.tys.param import Parameter
from guppylang_internals.tys.subst import Inst
from guppylang_internals.tys.ty import (
    FunctionType,
)

T = TypeVar("T")
P = ParamSpec("P")


def get_calling_frame() -> FrameType:
    """Finds the first frame that called this function outside the compiler modules."""
    frame = inspect.currentframe()
    while frame:
        module = inspect.getmodule(frame)
        if module is None:
            return frame
        if module.__file__ != __file__:
            return frame
        frame = frame.f_back
    raise RuntimeError("Couldn't obtain stack frame for definition")


def custom_function(
    compiler: CustomInoutCallCompiler | None = None,
    checker: CustomCallChecker | None = None,
    higher_order_value: bool = True,
    name: str = "",
    signature: FunctionType | None = None,
) -> Callable[[Callable[P, T]], GuppyFunctionDefinition[P, T]]:
    """Decorator to add custom typing or compilation behaviour to function decls.

    Optionally, usage of the function as a higher-order value can be disabled. In
    that case, the function signature can be omitted if a custom call compiler is
    provided.
    """

    def dec(f: Callable[P, T]) -> GuppyFunctionDefinition[P, T]:
        call_checker = checker or DefaultCallChecker()
        func = RawCustomFunctionDef(
            DefId.fresh(),
            name or f.__name__,
            None,
            f,
            call_checker,
            compiler or NotImplementedCallCompiler(),
            higher_order_value,
            signature,
        )
        DEF_STORE.register_def(func, get_calling_frame())
        return GuppyFunctionDefinition(func)

    return dec


def hugr_op(
    op: Callable[[ht.FunctionType, Inst, CompilerContext], ops.DataflowOp],
    checker: CustomCallChecker | None = None,
    higher_order_value: bool = True,
    name: str = "",
    signature: FunctionType | None = None,
) -> Callable[[Callable[P, T]], GuppyFunctionDefinition[P, T]]:
    """Decorator to annotate function declarations as HUGR ops.

    Args:
        op: A function that takes an instantiation of the type arguments as well as
            the inferred input and output types and returns a concrete HUGR op.
        checker: The custom call checker.
        higher_order_value: Whether the function may be used as a higher-order
            value.
        name: The name of the function.
    """
    return custom_function(OpCompiler(op), checker, higher_order_value, name, signature)


def extend_type(defn: TypeDef) -> Callable[[type], type]:
    """Decorator to add new instance functions to a type."""

    def dec(c: type) -> type:
        for val in c.__dict__.values():
            if isinstance(val, GuppyDefinition):
                DEF_STORE.register_impl(defn.id, val.wrapped.name, val.id)
        return c

    return dec


def custom_type(
    hugr_ty: ht.Type | Callable[[Sequence[Argument], CompilerContext], ht.Type],
    name: str = "",
    copyable: bool = True,
    droppable: bool = True,
    bound: ht.TypeBound | None = None,
    params: Sequence[Parameter] | None = None,
) -> Callable[[type[T]], type[T]]:
    """Decorator to annotate a class definitions as Guppy types.

    Requires the static Hugr translation of the type. Additionally, the type can be
    marked as linear. All `@guppy` annotated functions on the class are turned into
    instance functions.

    For non-generic types, the Hugr representation can be passed as a static value.
    For generic types, a callable may be passed that takes the type arguments of a
    concrete instantiation.
    """
    mk_hugr_ty = (
        (lambda args, ctx: hugr_ty) if isinstance(hugr_ty, ht.Type) else hugr_ty
    )

    def dec(c: type[T]) -> type[T]:
        defn = OpaqueTypeDef(
            DefId.fresh(),
            name or c.__name__,
            None,
            params or [],
            not copyable,
            not droppable,
            mk_hugr_ty,
            bound,
        )
        DEF_STORE.register_def(defn, get_calling_frame())
        for val in c.__dict__.values():
            if isinstance(val, GuppyDefinition):
                DEF_STORE.register_impl(defn.id, val.wrapped.name, val.id)
        # We're pretending to return the class unchanged, but in fact we return
        # a `GuppyDefinition` that handles the comptime logic
        return GuppyDefinition(defn)  # type: ignore[return-value]

    return dec


# TODO sphinx hack for custom decorators
