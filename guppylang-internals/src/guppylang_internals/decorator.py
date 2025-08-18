from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, ParamSpec, TypeVar

from hugr import ext as he
from hugr import ops
from hugr import tys as ht

from guppylang.defs import GuppyDefinition, GuppyFunctionDefinition
from guppylang_internals.compiler.core import (
    CompilerContext,
    GlobalConstId,
)
from guppylang_internals.definition.common import DefId
from guppylang_internals.definition.custom import (
    CustomCallChecker,
    CustomFunctionDef,
    CustomInoutCallCompiler,
    DefaultCallChecker,
    NotImplementedCallCompiler,
    OpCompiler,
    RawCustomFunctionDef,
)
from guppylang_internals.definition.function import RawFunctionDef
from guppylang_internals.definition.lowerable import RawLowerableFunctionDef
from guppylang_internals.definition.ty import OpaqueTypeDef, TypeDef
from guppylang_internals.definition.wasm import RawWasmFunctionDef
from guppylang_internals.dummy_decorator import _dummy_custom_decorator, sphinx_running
from guppylang_internals.engine import DEF_STORE
from guppylang_internals.std._internal.checker import WasmCallChecker
from guppylang_internals.std._internal.compiler.wasm import (
    WasmModuleCallCompiler,
    WasmModuleDiscardCompiler,
    WasmModuleInitCompiler,
)
from guppylang_internals.tys.builtin import (
    WasmModuleTypeDef,
)
from guppylang_internals.tys.ty import (
    FuncInput,
    FunctionType,
    InputFlags,
    NoneType,
    NumericType,
)

if TYPE_CHECKING:
    import builtins
    from collections.abc import Callable, Sequence
    from types import FrameType

    from guppylang_internals.tys.arg import Argument
    from guppylang_internals.tys.param import Parameter
    from guppylang_internals.tys.subst import Inst

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
    from guppylang.defs import GuppyFunctionDefinition

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


def lowerable_op(
    hugr_ext: he.Extension,
    checker: CustomCallChecker | None = None,
    higher_order_value: bool = True,
) -> Callable[[Callable[P, T]], GuppyFunctionDefinition[P, T]]:
    """Decorator to automatically generate a hugr OpDef and add to the user-provided
    hugr extension.

    Args:
        hugr_ext: Hugr extension for the hugr OpDef to be added
    """

    def dec(f: Callable[P, T]) -> GuppyFunctionDefinition[P, T]:
        defn = RawFunctionDef(DefId.fresh(), f.__name__, None, f)
        DEF_STORE.register_def(defn, get_calling_frame())

        defn = GuppyDefinition(defn)

        compiled_defn = defn.compile()

        try:
            func_op = next(
                data.op
                for _, data in compiled_defn.modules[0].nodes()
                if isinstance(data.op, ops.FuncDefn) and data.op.f_name == f.__name__
            )
        except StopIteration as e:
            raise NameError(
                f"Function definition ({f.__name__}) not found in hugr."
            ) from e

        op_def = he.OpDef(
            name=f.__name__,
            description=f.__doc__ or "",
            signature=he.OpDefSig(poly_func=func_op.signature),
            lower_funcs=[
                he.FixedHugr(
                    ht.ExtensionSet([ext.name for ext in compiled_defn.extensions]),
                    module,
                )
                for module in compiled_defn.modules
            ],
        )

        hugr_ext.add_op_def(op_def)

        def op(ty: ht.FunctionType, inst: Inst, ctx: CompilerContext) -> ops.DataflowOp:
            return ops.ExtOp(op_def, ty, [arg.to_hugr(ctx) for arg in inst])

        call_checker = checker or DefaultCallChecker()

        func = RawLowerableFunctionDef(
            DefId.fresh(),
            f.__name__,
            None,
            f,
            call_checker,
            OpCompiler(op),
            higher_order_value,
            None,
        )
        DEF_STORE.register_def(func, get_calling_frame())
        return GuppyFunctionDefinition(func)

    return dec


def extend_type(defn: TypeDef) -> Callable[[type], type]:
    """Decorator to add new instance functions to a type."""
    from guppylang.defs import GuppyDefinition

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
    from guppylang.defs import GuppyDefinition

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


def wasm_module(
    filename: str, filehash: int
) -> Callable[[builtins.type[T]], GuppyDefinition]:
    from guppylang.defs import GuppyDefinition

    def dec(cls: builtins.type[T]) -> GuppyDefinition:
        # N.B. Only one module per file and vice-versa
        wasm_module = WasmModuleTypeDef(
            DefId.fresh(),
            cls.__name__,
            None,
            filename,
            filehash,
        )

        wasm_module_ty = wasm_module.check_instantiate([], None)

        DEF_STORE.register_def(wasm_module, get_calling_frame())
        for val in cls.__dict__.values():
            if isinstance(val, GuppyDefinition):
                DEF_STORE.register_impl(wasm_module.id, val.wrapped.name, val.id)
        # Add a constructor to the class
        call_method = CustomFunctionDef(
            DefId.fresh(),
            "__new__",
            None,
            FunctionType(
                [FuncInput(NumericType(NumericType.Kind.Nat), flags=InputFlags.Owned)],
                wasm_module_ty,
            ),
            DefaultCallChecker(),
            WasmModuleInitCompiler(),
            True,
            GlobalConstId.fresh(f"{cls.__name__}.__new__"),
            True,
        )
        discard = CustomFunctionDef(
            DefId.fresh(),
            "discard",
            None,
            FunctionType([FuncInput(wasm_module_ty, InputFlags.Owned)], NoneType()),
            DefaultCallChecker(),
            WasmModuleDiscardCompiler(),
            False,
            GlobalConstId.fresh(f"{cls.__name__}.__discard__"),
            True,
        )
        DEF_STORE.register_def(call_method, get_calling_frame())
        DEF_STORE.register_impl(wasm_module.id, "__new__", call_method.id)
        DEF_STORE.register_def(discard, get_calling_frame())
        DEF_STORE.register_impl(wasm_module.id, "discard", discard.id)

        return GuppyDefinition(wasm_module)

    return dec


def wasm(f: Callable[P, T]) -> GuppyFunctionDefinition[P, T]:
    from guppylang.defs import GuppyFunctionDefinition

    func = RawWasmFunctionDef(
        DefId.fresh(),
        f.__name__,
        None,
        f,
        WasmCallChecker(),
        WasmModuleCallCompiler(f.__name__),
        True,
        signature=None,
    )
    DEF_STORE.register_def(func, get_calling_frame())
    return GuppyFunctionDefinition(func)


# Override decorators with dummy versions if we're running a sphinx build
if not TYPE_CHECKING and sphinx_running():
    custom_function = _dummy_custom_decorator
    hugr_op = _dummy_custom_decorator
    extend_type = _dummy_custom_decorator
    custom_type = _dummy_custom_decorator
    wasm_module = _dummy_custom_decorator
    wasm = _dummy_custom_decorator()
