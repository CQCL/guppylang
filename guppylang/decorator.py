import ast
import builtins
import inspect
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import FrameType, ModuleType
from typing import Any, TypeVar, cast

from hugr import ops
from hugr import tys as ht
from hugr import val as hv
from hugr.package import FuncDefnPointer, ModulePointer
from typing_extensions import dataclass_transform

from guppylang.ast_util import annotate_location
from guppylang.compiler.core import CompilerContext
from guppylang.definition.common import DefId
from guppylang.definition.const import RawConstDef
from guppylang.definition.custom import (
    CustomCallChecker,
    CustomInoutCallCompiler,
    DefaultCallChecker,
    NotImplementedCallCompiler,
    OpCompiler,
    RawCustomFunctionDef,
)
from guppylang.definition.declaration import RawFunctionDecl
from guppylang.definition.extern import RawExternDef
from guppylang.definition.function import (
    CompiledFunctionDef,
    RawFunctionDef,
)
from guppylang.definition.overloaded import OverloadedFunctionDef
from guppylang.definition.parameter import ConstVarDef, TypeVarDef
from guppylang.definition.pytket_circuits import (
    CompiledPytketDef,
    RawLoadPytketDef,
    RawPytketDef,
)
from guppylang.definition.struct import RawStructDef
from guppylang.definition.traced import RawTracedFunctionDef
from guppylang.definition.ty import OpaqueTypeDef, TypeDef
from guppylang.dummy_decorator import _DummyGuppy, sphinx_running
from guppylang.engine import DEF_STORE
from guppylang.span import Loc, SourceMap, Span
from guppylang.tracing.object import GuppyDefinition, TypeVarGuppyDefinition
from guppylang.tys.arg import Argument
from guppylang.tys.param import Parameter
from guppylang.tys.subst import Inst
from guppylang.tys.ty import FunctionType, NoneType, NumericType

S = TypeVar("S")
T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])
Decorator = Callable[[S], T]

AnyRawFunctionDef = (
    RawFunctionDef,
    RawCustomFunctionDef,
    RawFunctionDecl,
    RawPytketDef,
    RawLoadPytketDef,
    OverloadedFunctionDef,
)


_JUPYTER_NOTEBOOK_MODULE = "<jupyter-notebook>"


@dataclass(frozen=True)
class ModuleIdentifier:
    """Identifier for the Python file/module that called the decorator."""

    filename: Path

    #: The name of the module. We only store this to have nice name to report back to
    #: the user. When determining whether two `ModuleIdentifier`s correspond to the same
    #: module, we only take the module path into account.
    name: str = field(compare=False)

    #: A reference to the python module
    module: ModuleType | None = field(compare=False)


class _Guppy:
    """Class for the `@guppy` decorator."""

    def __call__(self, f: F) -> F:
        defn = RawFunctionDef(DefId.fresh(), f.__name__, None, f)
        DEF_STORE.register_def(defn, get_calling_frame())
        # We're pretending to return the function unchanged, but in fact we return
        # a `GuppyDefinition` that handles the comptime logic
        return GuppyDefinition(defn)  # type: ignore[return-value]

    def comptime(self, f: F) -> F:
        defn = RawTracedFunctionDef(DefId.fresh(), f.__name__, None, f)
        DEF_STORE.register_def(defn, get_calling_frame())
        # We're pretending to return the function unchanged, but in fact we return
        # a `GuppyDefinition` that handles the comptime logic
        return GuppyDefinition(defn)  # type: ignore[return-value]

    def extend_type(self, defn: TypeDef) -> Callable[[type], type]:
        """Decorator to add new instance functions to a type."""

        def dec(c: type) -> type:
            for val in c.__dict__.values():
                if isinstance(val, GuppyDefinition):
                    DEF_STORE.register_impl(defn.id, val.wrapped.name, val.id)
            return c

        return dec

    def type(
        self,
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

    @dataclass_transform()
    def struct(self, cls: builtins.type[T]) -> builtins.type[T]:
        defn = RawStructDef(DefId.fresh(), cls.__name__, None, cls)
        DEF_STORE.register_def(defn, get_calling_frame())
        for val in cls.__dict__.values():
            if isinstance(val, GuppyDefinition):
                DEF_STORE.register_impl(defn.id, val.wrapped.name, val.id)
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
        return TypeVarGuppyDefinition(defn, TypeVar(name))  # type: ignore[return-value]

    def nat_var(self, name: str) -> TypeVar:
        """Creates a new const nat variable in a module."""
        defn = ConstVarDef(DefId.fresh(), name, None, NumericType(NumericType.Kind.Nat))
        DEF_STORE.register_def(defn, get_calling_frame())
        # We're pretending to return a `typing.TypeVar`, but in fact we return a special
        # `GuppyDefinition` that pretends to be a TypeVar at runtime
        return TypeVarGuppyDefinition(defn, TypeVar(name))  # type: ignore[return-value]

    def custom(
        self,
        compiler: CustomInoutCallCompiler | None = None,
        checker: CustomCallChecker | None = None,
        higher_order_value: bool = True,
        name: str = "",
        signature: FunctionType | None = None,
    ) -> Callable[[F], F]:
        """Decorator to add custom typing or compilation behaviour to function decls.

        Optionally, usage of the function as a higher-order value can be disabled. In
        that case, the function signature can be omitted if a custom call compiler is
        provided.
        """

        def dec(f: F) -> F:
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
            # We're pretending to return the function unchanged, but in fact we return
            # a `GuppyDefinition` that handles the comptime logic
            return GuppyDefinition(func)  # type: ignore[return-value]

        return dec

    def hugr_op(
        self,
        op: Callable[[ht.FunctionType, Inst, CompilerContext], ops.DataflowOp],
        checker: CustomCallChecker | None = None,
        higher_order_value: bool = True,
        name: str = "",
        signature: FunctionType | None = None,
    ) -> Callable[[F], F]:
        """Decorator to annotate function declarations as HUGR ops.

        Args:
            op: A function that takes an instantiation of the type arguments as well as
                the inferred input and output types and returns a concrete HUGR op.
            checker: The custom call checker.
            higher_order_value: Whether the function may be used as a higher-order
                value.
            name: The name of the function.
        """
        return self.custom(OpCompiler(op), checker, higher_order_value, name, signature)

    def declare(self, f: F) -> F:
        defn = RawFunctionDecl(DefId.fresh(), f.__name__, None, f)
        DEF_STORE.register_def(defn, get_calling_frame())
        # We're pretending to return the function unchanged, but in fact we return
        # a `GuppyDefinition` that handles the comptime logic
        return GuppyDefinition(defn)  # type: ignore[return-value]

    def overload(self, *funcs: Any) -> Callable[[F], F]:
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

        def dec(f: F) -> F:
            dummy_sig = FunctionType([], NoneType())
            defn = OverloadedFunctionDef(
                DefId.fresh(), f.__name__, None, dummy_sig, func_ids
            )
            DEF_STORE.register_def(defn, get_calling_frame())
            # We're pretending to return the class unchanged, but in fact we return
            # a `GuppyDefinition` that handles the comptime logic
            return GuppyDefinition(defn)  # type: ignore[return-value]

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

    def extern(
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

    def check(self, obj: Any) -> None:
        """Compiles a Guppy definition to Hugr."""
        from guppylang.engine import ENGINE

        if not isinstance(obj, GuppyDefinition):
            raise TypeError(f"Object is not a Guppy definition: {obj}")
        return ENGINE.check(obj.id)

    def compile(self, obj: Any) -> ModulePointer:
        """Compiles a Guppy definition to Hugr."""
        from guppylang.engine import ENGINE

        if not isinstance(obj, GuppyDefinition):
            raise TypeError(f"Object is not a Guppy definition: {obj}")
        return ENGINE.compile(obj.id)

    def compile_function(
        self,
        obj: Any,
    ) -> FuncDefnPointer:
        """Compiles a single function definition."""
        from guppylang.engine import ENGINE

        if not isinstance(obj, GuppyDefinition):
            raise TypeError(f"Object is not a Guppy definition: {obj}")
        compiled_module = ENGINE.compile(obj.id)
        compiled_def = ENGINE.compiled[obj.id]
        assert isinstance(compiled_def, CompiledFunctionDef | CompiledPytketDef)
        node = compiled_def.func_def.parent_node
        return FuncDefnPointer(
            compiled_module.package, compiled_module.module_index, node
        )

    def pytket(self, input_circuit: Any) -> Callable[[F], F]:
        """Adds a pytket circuit function definition with explicit signature."""
        err_msg = "Only pytket circuits can be passed to guppy.pytket"
        try:
            import pytket

            if not isinstance(input_circuit, pytket.circuit.Circuit):
                raise TypeError(err_msg) from None

        except ImportError:
            raise TypeError(err_msg) from None

        def func(f: F) -> F:
            defn = RawPytketDef(DefId.fresh(), f.__name__, None, f, input_circuit)
            DEF_STORE.register_def(defn, get_calling_frame())
            # We're pretending to return the function unchanged, but in fact we return
            # a `GuppyDefinition` that handles the comptime logic
            return GuppyDefinition(defn)  # type: ignore[return-value]

        return func

    def load_pytket(
        self,
        name: str,
        input_circuit: Any,
        *,
        use_arrays: bool = True,
    ) -> GuppyDefinition:
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
        return GuppyDefinition(defn)


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
    object.__setattr__(f, "__custom_guppy_decorator__", True)
    return f


def get_calling_frame() -> FrameType:
    """Finds the first frame that called this function outside the compiler modules."""
    frame = inspect.currentframe()
    while frame:
        # Skip frame if we're inside a user-defined decorator that wraps the `guppy`
        # decorator. Those are functions that have a `__custom_guppy_decorator__` field.
        # We can get a reference to the calling function by looking up the code function
        # name in the frame globals:
        func = frame.f_globals.get(frame.f_code.co_name)
        if getattr(func, "__custom_guppy_decorator__", None) is True:
            frame = frame.f_back
            continue
        module = inspect.getmodule(frame)
        if module is None:
            return frame
        if module.__file__ != __file__:
            return frame
        frame = frame.f_back
    raise RuntimeError("Couldn't obtain stack frame for definition")


guppy = cast(_Guppy, _DummyGuppy()) if sphinx_running() else _Guppy()
