import ast
import builtins
import inspect
from collections.abc import Callable, Sequence
from types import FrameType
from typing import Any, ParamSpec, TypeVar, cast

from hugr import ops
from hugr import tys as ht
from hugr import val as hv
from hugr.package import ModulePointer
from typing_extensions import dataclass_transform, deprecated

from guppylang_internals.ast_util import annotate_location
from guppylang_internals.compiler.core import (
    CompilerContext,
    GlobalConstId,
)
from guppylang_internals.definition.common import DefId
from guppylang_internals.definition.const import RawConstDef
from guppylang_internals.definition.custom import (
    CustomCallChecker,
    CustomFunctionDef,
    CustomInoutCallCompiler,
    DefaultCallChecker,
    NotImplementedCallCompiler,
    OpCompiler,
    RawCustomFunctionDef,
)
from guppylang_internals.definition.declaration import RawFunctionDecl
from guppylang_internals.definition.extern import RawExternDef
from guppylang_internals.definition.function import (
    RawFunctionDef,
)
from guppylang_internals.definition.overloaded import OverloadedFunctionDef
from guppylang_internals.definition.parameter import ConstVarDef, RawConstVarDef, TypeVarDef
from guppylang_internals.definition.pytket_circuits import (
    RawLoadPytketDef,
    RawPytketDef,
)
from guppylang_internals.definition.struct import RawStructDef
from guppylang_internals.definition.traced import RawTracedFunctionDef
from guppylang_internals.definition.ty import OpaqueTypeDef, TypeDef
from guppylang_internals.definition.wasm import RawWasmFunctionDef
from guppylang_internals.defs import (
    GuppyDefinition,
    GuppyFunctionDefinition,
    GuppyTypeVarDefinition,
)
from guppylang_internals.dummy_decorator import _DummyGuppy, sphinx_running
from guppylang_internals.engine import DEF_STORE
from guppylang_internals.span import Loc, SourceMap, Span
from guppylang_internals.std._internal.checker import WasmCallChecker
from guppylang_internals.std._internal.compiler.wasm import (
    WasmModuleCallCompiler,
    WasmModuleDiscardCompiler,
    WasmModuleInitCompiler,
)
from guppylang_internals.tys.arg import Argument
from guppylang_internals.tys.builtin import (
    WasmModuleTypeDef,
)
from guppylang_internals.tys.param import Parameter
from guppylang_internals.tys.subst import Inst
from guppylang_internals.tys.ty import (
    FuncInput,
    FunctionType,
    InputFlags,
    NoneType,
    NumericType,
)

S = TypeVar("S")
T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])
P = ParamSpec("P")
Decorator = Callable[[S], T]

AnyRawFunctionDef = (
    RawFunctionDef,
    RawCustomFunctionDef,
    RawFunctionDecl,
    RawPytketDef,
    RawLoadPytketDef,
    OverloadedFunctionDef,
)


class _Guppy:
    """Class for the `@guppy` decorator."""

    def __call__(self, f: Callable[P, T]) -> GuppyFunctionDefinition[P, T]:
        defn = RawFunctionDef(DefId.fresh(), f.__name__, None, f)
        DEF_STORE.register_def(defn, get_calling_frame())
        return GuppyFunctionDefinition(defn)

    def comptime(self, f: Callable[P, T]) -> GuppyFunctionDefinition[P, T]:
        defn = RawTracedFunctionDef(DefId.fresh(), f.__name__, None, f)
        DEF_STORE.register_def(defn, get_calling_frame())
        return GuppyFunctionDefinition(defn)

    @deprecated("Use @extend_type instead.")
    def extend_type(self, defn: TypeDef) -> Callable[[type], type]:
        return extend_type(defn)

    @deprecated("Use @custom_type instead.")
    def type(
        self,
        hugr_ty: ht.Type | Callable[[Sequence[Argument], CompilerContext], ht.Type],
        name: str = "",
        copyable: bool = True,
        droppable: bool = True,
        bound: ht.TypeBound | None = None,
        params: Sequence[Parameter] | None = None,
    ) -> Callable[[type[T]], type[T]]:
        return custom_type(hugr_ty, name, copyable, droppable, bound, params)

    @dataclass_transform()
    def struct(self, cls: builtins.type[T]) -> builtins.type[T]:
        defn = RawStructDef(DefId.fresh(), cls.__name__, None, cls)
        frame = get_calling_frame()
        DEF_STORE.register_def(defn, frame)
        for val in cls.__dict__.values():
            if isinstance(val, GuppyDefinition):
                DEF_STORE.register_impl(defn.id, val.wrapped.name, val.id)
        # Prior to Python 3.13, the `__firstlineno__` attribute on classes is not set.
        # However, we need this information to precisely look up the source for the
        # class later. If it's not there, we can set it from the calling frame:
        if not hasattr(cls, "__firstlineno__"):
            cls.__firstlineno__ = frame.f_lineno  # type: ignore[attr-defined]
        # We're pretending to return the class unchanged, but in fact we return
        # a `GuppyDefinition` that handles the comptime logic
        return GuppyDefinition(defn)  # type: ignore[return-value]

    def type_var(
        self,
        name: str,
        copyable: bool = True,
        droppable: bool = True,
    ) -> TypeVar:
        """Creates a new type variable in a module."""
        defn = TypeVarDef(DefId.fresh(), name, None, copyable, droppable)
        DEF_STORE.register_def(defn, get_calling_frame())
        # We're pretending to return a `typing.TypeVar`, but in fact we return a special
        # `GuppyDefinition` that pretends to be a TypeVar at runtime
        return GuppyTypeVarDefinition(defn, TypeVar(name))  # type: ignore[return-value]

    def nat_var(self, name: str) -> TypeVar:
        """Creates a new const nat variable in a module."""
        defn = ConstVarDef(DefId.fresh(), name, None, NumericType(NumericType.Kind.Nat))
        DEF_STORE.register_def(defn, get_calling_frame())
        # We're pretending to return a `typing.TypeVar`, but in fact we return a special
        # `GuppyDefinition` that pretends to be a TypeVar at runtime
        return GuppyTypeVarDefinition(defn, TypeVar(name))  # type: ignore[return-value]

    def const_var(self, name: str, ty: str) -> TypeVar:
        """Creates a new const type variable."""
        type_ast = _parse_expr_string(
            ty, f"Not a valid Guppy type: `{ty}`", DEF_STORE.sources
        )
        defn = RawConstVarDef(DefId.fresh(), name, None, type_ast)
        DEF_STORE.register_def(defn, get_calling_frame())
        # We're pretending to return a `typing.TypeVar`, but in fact we return a special
        # `GuppyDefinition` that pretends to be a TypeVar at runtime
        return GuppyTypeVarDefinition(defn, TypeVar(name))  # type: ignore[return-value]

    @deprecated("Use @custom_function instead.")
    def custom(
        self,
        compiler: CustomInoutCallCompiler | None = None,
        checker: CustomCallChecker | None = None,
        higher_order_value: bool = True,
        name: str = "",
        signature: FunctionType | None = None,
    ) -> Callable[[Callable[P, T]], GuppyFunctionDefinition[P, T]]:
        return custom_function(compiler, checker, higher_order_value, name, signature)

    @deprecated("Use @hugr_op instead.")
    def hugr_op(
        self,
        op: Callable[[ht.FunctionType, Inst, CompilerContext], ops.DataflowOp],
        checker: CustomCallChecker | None = None,
        higher_order_value: bool = True,
        name: str = "",
        signature: FunctionType | None = None,
    ) -> Callable[[Callable[P, T]], GuppyFunctionDefinition[P, T]]:
        return hugr_op(op, checker, higher_order_value, name, signature)

    def declare(self, f: Callable[P, T]) -> GuppyFunctionDefinition[P, T]:
        defn = RawFunctionDecl(DefId.fresh(), f.__name__, None, f)
        DEF_STORE.register_def(defn, get_calling_frame())
        return GuppyFunctionDefinition(defn)

    def overload(
        self, *funcs: Any
    ) -> Callable[[Callable[P, T]], GuppyFunctionDefinition[P, T]]:
        """Collects multiple function definitions into one overloaded function.

        Consider the following example:

        ```
        @guppy.declare
        def variant1(x: int, y: int) -> int: ...

        @guppy.declare
        def variant2(x: float) -> int: ...

        @guppy.overload(variant1, variant2)
        def combined(): ...
        ```

        Now, `combined` may be called with either one `float` or two `int` arguments,
        delegating to the implementation with the matching signature:

        ```
        combined(4.2)  # Calls `variant1`
        combined(42, 43)  # Calls `variant2`
        ```

        Note that the compiler will pick the *first* implementation with matching
        signature and ignore all following ones, even if they would also match. For
        example, if we added a third variant

        ```
        @guppy.declare
        def variant3(x: int) -> int: ...

        @guppy.overload(variant1, variant2, variant3)
        def combined_new(): ...
        ```

        then a call `combined_new(42)` will still select the `variant1` implementation
        `42` is a valid argument for `variant1` and `variant1` comes before `variant3`
        in the `@guppy.overload` annotation.
        """
        funcs = list(funcs)
        if len(funcs) < 2:
            raise ValueError("Overload requires at least two functions")
        func_ids = []
        for func in funcs:
            if not isinstance(func, GuppyDefinition):
                raise TypeError(f"Not a Guppy definition: {func}")
            if not isinstance(func.wrapped, AnyRawFunctionDef):
                raise TypeError(
                    f"Not a Guppy function definition: {func.wrapped.description} "
                    f"`{func.wrapped.name}`"
                )
            func_ids.append(func.id)

        def dec(f: Callable[P, T]) -> GuppyFunctionDefinition[P, T]:
            dummy_sig = FunctionType([], NoneType())
            defn = OverloadedFunctionDef(
                DefId.fresh(), f.__name__, None, dummy_sig, func_ids
            )
            DEF_STORE.register_def(defn, get_calling_frame())
            return GuppyFunctionDefinition(defn)

        return dec

    def constant(self, name: str, ty: str, value: hv.Value) -> T:  # type: ignore[type-var]  # Since we're returning a free type variable
        """Adds a constant to a module, backed by a `hugr.val.Value`."""
        type_ast = _parse_expr_string(
            ty, f"Not a valid Guppy type: `{ty}`", DEF_STORE.sources
        )
        defn = RawConstDef(DefId.fresh(), name, None, type_ast, value)
        DEF_STORE.register_def(defn, get_calling_frame())
        # We're pretending to return a free type variable, but in fact we return
        # a `GuppyDefinition` that handles the comptime logic
        return GuppyDefinition(defn)  # type: ignore[return-value]

    def _extern(
        self,
        name: str,
        ty: str,
        symbol: str | None = None,
        constant: bool = True,
    ) -> T:  # type: ignore[type-var]  # Since we're returning a free type variable
        """Adds an extern symbol to a module."""
        type_ast = _parse_expr_string(
            ty, f"Not a valid Guppy type: `{ty}`", DEF_STORE.sources
        )
        defn = RawExternDef(
            DefId.fresh(), name, None, symbol or name, constant, type_ast
        )
        DEF_STORE.register_def(defn, get_calling_frame())
        # We're pretending to return a free type variable, but in fact we return
        # a `GuppyDefinition` that handles the comptime logic
        return GuppyDefinition(defn)  # type: ignore[return-value]

    @deprecated(
        "foo.compile() is deprecated and will be removed in a future version"
        " use foo.compile() instead."
    )
    def compile(self, obj: Any) -> ModulePointer:
        """Compiles a Guppy definition to Hugr."""

        if not isinstance(obj, GuppyDefinition):
            raise TypeError(f"Object is not a Guppy definition: {obj}")
        return ModulePointer(obj.compile(), 0)

    def pytket(
        self, input_circuit: Any
    ) -> Callable[[Callable[P, T]], GuppyFunctionDefinition[P, T]]:
        """Adds a pytket circuit function definition with explicit signature."""
        err_msg = "Only pytket circuits can be passed to guppy.pytket"
        try:
            import pytket

            if not isinstance(input_circuit, pytket.circuit.Circuit):
                raise TypeError(err_msg) from None

        except ImportError:
            raise TypeError(err_msg) from None

        def func(f: Callable[P, T]) -> GuppyFunctionDefinition[P, T]:
            defn = RawPytketDef(DefId.fresh(), f.__name__, None, f, input_circuit)
            DEF_STORE.register_def(defn, get_calling_frame())
            return GuppyFunctionDefinition(defn)

        return func

    def load_pytket(
        self,
        name: str,
        input_circuit: Any,
        *,
        use_arrays: bool = True,
    ) -> GuppyFunctionDefinition[..., Any]:
        """Adds a pytket circuit function definition with implicit signature."""
        err_msg = "Only pytket circuits can be passed to guppy.load_pytket"
        try:
            import pytket

            if not isinstance(input_circuit, pytket.circuit.Circuit):
                raise TypeError(err_msg) from None

        except ImportError:
            raise TypeError(err_msg) from None

        span = _find_load_call(DEF_STORE.sources)
        defn = RawLoadPytketDef(
            DefId.fresh(), name, None, span, input_circuit, use_arrays
        )
        DEF_STORE.register_def(defn, get_calling_frame())
        return GuppyFunctionDefinition(defn)

    def wasm_module(
        self, filename: str, filehash: int
    ) -> Decorator[builtins.type[T], GuppyDefinition]:
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
                    [
                        FuncInput(
                            NumericType(NumericType.Kind.Nat), flags=InputFlags.Owned
                        )
                    ],
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

    def wasm(self, f: Callable[P, T]) -> GuppyFunctionDefinition[P, T]:
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


def _parse_expr_string(ty_str: str, parse_err: str, sources: SourceMap) -> ast.expr:
    """Helper function to parse expressions that are provided as strings.

    Tries to infer the source location were the given string was defined by inspecting
    the call stack.
    """
    try:
        expr_ast = ast.parse(ty_str, mode="eval").body
    except SyntaxError:
        raise SyntaxError(parse_err) from None

    # Try to annotate the type AST with source information. This requires us to
    # inspect the stack frame of the caller
    if caller_frame := get_calling_frame():
        info = inspect.getframeinfo(caller_frame)
        if caller_module := inspect.getmodule(caller_frame):
            sources.add_file(info.filename)
            source_lines, _ = inspect.getsourcelines(caller_module)
            source = "".join(source_lines)
            annotate_location(expr_ast, source, info.filename, 1)
            # Modify the AST so that all sub-nodes span the entire line. We
            # can't give a better location since we don't know the column
            # offset of the `ty` argument
            for node in [expr_ast, *ast.walk(expr_ast)]:
                node.lineno = node.end_lineno = info.lineno
                node.col_offset = 0
                node.end_col_offset = len(source_lines[info.lineno - 1]) - 1
    return expr_ast


def _find_load_call(sources: SourceMap) -> Span | None:
    """Helper function to find location where pytket circuit was loaded.

    Tries to define a source code span by inspecting the call stack.
    """
    # Go back as first frame outside of compiler modules is 'pretty_errors_wrapped'.
    if load_frame := get_calling_frame():
        info = inspect.getframeinfo(load_frame)
        filename = info.filename
        lineno = info.lineno
        sources.add_file(filename)
        # If we don't support python <= 3.10, this can be done better with
        # info.positions which gives you exact offsets.
        # For now over approximate and make the span cover the entire line.
        if load_module := inspect.getmodule(load_frame):
            source_lines, _ = inspect.getsourcelines(load_module)
            max_offset = len(source_lines[lineno - 1]) - 1

            start = Loc(filename, lineno, 0)
            end = Loc(filename, lineno, max_offset)
            return Span(start, end)
    return None


def custom_guppy_decorator(f: F) -> F:
    """Decorator to mark user-defined decorators that wrap builtin `guppy` decorators.

    Example:

    ```
    @custom_guppy_decorator
    def my_guppy(f):
        # Some custom logic here ...
        return guppy(f)

    @my_guppy
    def main() -> int: ...
    ```

    If the `custom_guppy_decorator` were missing, then the `@my_guppy` annotation would
    not produce a valid guppy definition.
    """
    f.__code__ = f.__code__.replace(co_name="__custom_guppy_decorator__")
    return f


def get_calling_frame() -> FrameType:
    """Finds the first frame that called this function outside the compiler modules."""
    frame = inspect.currentframe()
    while frame:
        # Skip frame if we're inside a user-defined decorator that wraps the `guppy`
        # decorator. Those are functions with a special `__code__.co_name` of
        # "__custom_guppy_decorator__".
        if frame.f_code.co_name == "__custom_guppy_decorator__":
            frame = frame.f_back
            continue
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


guppy = cast(_Guppy, _DummyGuppy()) if sphinx_running() else _Guppy()

# TODO sphinx hack for other decorators
