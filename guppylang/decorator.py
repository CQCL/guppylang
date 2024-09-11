import ast
import inspect
from collections.abc import Callable, KeysView
from dataclasses import dataclass, field
from pathlib import Path
from types import FrameType, ModuleType
from typing import Any, TypeVar, overload

import hugr.ext
from hugr import ops
from hugr import tys as ht
from hugr import val as hv

import guppylang
from guppylang.ast_util import annotate_location, has_empty_body
from guppylang.definition.common import DefId, Definition
from guppylang.definition.const import RawConstDef
from guppylang.definition.custom import (
    CustomCallChecker,
    CustomCallCompiler,
    DefaultCallChecker,
    NotImplementedCallCompiler,
    OpCompiler,
    RawCustomFunctionDef,
)
from guppylang.definition.declaration import RawFunctionDecl
from guppylang.definition.extern import RawExternDef
from guppylang.definition.function import RawFunctionDef, parse_py_func
from guppylang.definition.parameter import ConstVarDef, TypeVarDef
from guppylang.definition.struct import RawStructDef
from guppylang.definition.ty import OpaqueTypeDef, TypeDef
from guppylang.error import GuppyError, MissingModuleError, pretty_errors
from guppylang.module import GuppyModule, PyFunc, find_guppy_module_in_py_module, \
    PyClass
from guppylang.tys.subst import Inst
from guppylang.tys.ty import NumericType

S = TypeVar("S")
T = TypeVar("T")
Decorator = Callable[[S], T]

FuncDefDecorator = Decorator[PyFunc, RawFunctionDef]
FuncDeclDecorator = Decorator[PyFunc, RawFunctionDecl]
CustomFuncDecorator = Decorator[PyFunc, RawCustomFunctionDef]
ClassDecorator = Decorator[PyClass, PyClass]
OpaqueTypeDecorator = Decorator[PyClass, OpaqueTypeDef]
StructDecorator = Decorator[PyClass, RawStructDef]


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

    # The currently-alive GuppyModules, associated with a Python file/module
    _modules: dict[ModuleIdentifier, GuppyModule]

    def __init__(self) -> None:
        self._modules = {}

    @overload
    def __call__(self, arg: PyFunc) -> RawFunctionDef: ...

    @overload
    def __call__(self, arg: GuppyModule) -> FuncDefDecorator: ...

    @pretty_errors
    def __call__(self, arg: PyFunc | GuppyModule) -> FuncDefDecorator | RawFunctionDef:
        """Decorator to annotate Python functions as Guppy code.

        Optionally, the `GuppyModule` in which the function should be placed can
        be passed to the decorator.
        """
        def dec(f: Callable[..., Any], module: GuppyModule) -> RawFunctionDef:
            return module.register_func_def(f)

        return self._with_optional_module(dec, arg)

    def _with_optional_module(self, dec: Callable[[S, GuppyModule], T], arg: S | GuppyModule) -> Callable[[S], T] | T:
        """Helper function to define decorators that take an optional `GuppyModule`
        argument but no other arguments.

        For example, we allow `@guppy(module)` but also `@guppy`.
        """
        if isinstance(arg, GuppyModule):
            return lambda s: dec(s, arg)
        return dec(arg, self.get_module())

    def _get_python_caller(self, fn: PyFunc | None = None) -> ModuleIdentifier:
        """Returns an identifier for the Python file/module that called the decorator.

        :param fn: Optional. The function that was decorated.
        """
        if fn is not None:
            filename = inspect.getfile(fn)
            module = inspect.getmodule(fn)
        else:
            frame = inspect.currentframe()
            while frame:
                info = inspect.getframeinfo(frame)
                if info and info.filename != __file__:
                    filename = info.filename
                    module = inspect.getmodule(frame)
                    # Skip frames from the `pretty_error` decorator
                    if module != guppylang.error:
                        break
                frame = frame.f_back
            else:
                raise GuppyError("Could not find a caller for the `@guppy` decorator")
        module_path = Path(filename)
        return ModuleIdentifier(
            module_path, module.__name__ if module else module_path.name, module
        )

    def init_module(self, import_builtins: bool = True) -> None:
        """Manually initialises a Guppy module for the current Python file.

        Calling this method is only required when trying to define an empty module or
        a module that doesn't include the builtins.
        """
        module_id = self._get_python_caller()
        if module_id in self._modules:
            msg = f"Module {module_id.name} is already initialised"
            raise GuppyError(msg)
        self._modules[module_id] = GuppyModule(module_id.name, import_builtins)

    @pretty_errors
    def extend_type(self, defn: TypeDef, module: GuppyModule | None = None) -> ClassDecorator:
        """Decorator to add new instance functions to a type."""
        mod = module or self.get_module()
        mod._instance_func_buffer = {}

        def dec(c: type) -> type:
            mod._register_buffered_instance_funcs(defn)
            return c

        return dec

    @pretty_errors
    def type(
        self,
        hugr_ty: ht.Type,
        name: str = "",
        linear: bool = False,
        bound: ht.TypeBound | None = None,
        module: GuppyModule | None = None,
    ) -> OpaqueTypeDecorator:
        """Decorator to annotate a class definitions as Guppy types.

        Requires the static Hugr translation of the type. Additionally, the type can be
        marked as linear. All `@guppy` annotated functions on the class are turned into
        instance functions.
        """
        mod = module or self.get_module()
        mod._instance_func_buffer = {}

        def dec(c: type) -> OpaqueTypeDef:
            defn = OpaqueTypeDef(
                DefId.fresh(mod),
                name or c.__name__,
                None,
                [],
                linear,
                lambda _: hugr_ty,
                bound,
            )
            mod.register_def(defn)
            mod._register_buffered_instance_funcs(defn)
            return defn

        return dec

    @property
    def struct(self) -> Callable[[PyClass | GuppyModule], StructDecorator | RawStructDef]:
        """Decorator to define a new struct."""
        # Note that this is a property. Thus, the code below is executed *before*
        # the members of the decorated class are executed.
        # At this point, we don't know if the user has called `@struct(module)` or
        # just `@struct`. To be safe, we initialise the method buffer of the implicit
        # module either way
        caller_id = self._get_python_caller()
        implicit_module_existed = caller_id in self._modules
        implicit_module = self.get_module(
            # But don't try to do implicit imports since we're not sure if this is
            # actually an implicit module
            resolve_implicit_imports=False
        )
        implicit_module._instance_func_buffer = {}

        def dec(cls: type, module: GuppyModule) -> RawStructDef:
            defn = RawStructDef(DefId.fresh(module), cls.__name__, None, cls)
            module.register_def(defn)
            module._register_buffered_instance_funcs(defn)
            # If we mistakenly initialised the method buffer of the implicit module
            # we can just clear it here
            if module != implicit_module:
                implicit_module._instance_func_buffer = None
                if not implicit_module_existed:
                    self._modules.pop(caller_id)
            return defn

        def higher_dec(arg: GuppyModule | PyFunc) -> StructDecorator | RawStructDef:
            if isinstance(arg, GuppyModule):
                arg._instance_func_buffer = {}
            return self._with_optional_module(dec, arg)

        return higher_dec

    @pretty_errors
    def type_var(self, name: str, linear: bool = False, module: GuppyModule | None = None) -> TypeVar:
        """Creates a new type variable in a module."""
        module = module or self.get_module()
        defn = TypeVarDef(DefId.fresh(module), name, None, linear)
        module.register_def(defn)
        # Return an actual Python `TypeVar` so it can be used as an actual type in code
        # that is executed by interpreter before handing it to Guppy.
        return TypeVar(name)

    @pretty_errors
    def nat_var(self, name: str, module: GuppyModule | None = None) -> ConstVarDef:
        """Creates a new const nat variable in a module."""
        module = module or self.get_module()
        defn = ConstVarDef(
            DefId.fresh(module), name, None, NumericType(NumericType.Kind.Nat)
        )
        module.register_def(defn)
        return defn

    @pretty_errors
    def custom(
        self,
        compiler: CustomCallCompiler | None = None,
        checker: CustomCallChecker | None = None,
        higher_order_value: bool = True,
        name: str = "",
        module: GuppyModule | None = None,
    ) -> CustomFuncDecorator:
        """Decorator to add custom typing or compilation behaviour to function decls.

        Optionally, usage of the function as a higher-order value can be disabled. In
        that case, the function signature can be omitted if a custom call compiler is
        provided.
        """
        mod = module or self.get_module()

        def dec(f: PyFunc) -> RawCustomFunctionDef:
            func_ast, docstring = parse_py_func(f)
            if not has_empty_body(func_ast):
                raise GuppyError(
                    "Body of custom function declaration must be empty",
                    func_ast.body[0],
                )
            call_checker = checker or DefaultCallChecker()
            func = RawCustomFunctionDef(
                DefId.fresh(mod),
                name or func_ast.name,
                func_ast,
                call_checker,
                compiler or NotImplementedCallCompiler(),
                higher_order_value,
            )
            mod.register_def(func)
            return func

        return dec

    def hugr_op(
        self,
        op: Callable[[ht.FunctionType, Inst], ops.DataflowOp],
        checker: CustomCallChecker | None = None,
        higher_order_value: bool = True,
        name: str = "",
        module: GuppyModule | None = None,
    ) -> CustomFuncDecorator:
        """Decorator to annotate function declarations as HUGR ops.

        Args:
            module: The module in which the function should be defined.
            op: A function that takes an instantiation of the type arguments as well as
                the inferred input and output types and returns a concrete HUGR op.
            checker: The custom call checker.
            higher_order_value: Whether the function may be used as a higher-order
                value.
            name: The name of the function.
        """
        return self.custom(OpCompiler(op), checker, higher_order_value, name, module)

    @overload
    def declare(self, arg: GuppyModule) -> RawFunctionDecl: ...

    @overload
    def declare(self, arg: PyFunc) -> FuncDeclDecorator: ...

    def declare(self, arg: GuppyModule | PyFunc) -> FuncDeclDecorator | RawFunctionDecl:
        """Decorator to declare functions"""

        def dec(f: Callable[..., Any], module: GuppyModule) -> RawFunctionDecl:
            return module.register_func_decl(f)

        return self._with_optional_module(dec, arg)

    def constant(
        self, name: str, ty: str, value: hv.Value, module: GuppyModule | None = None
    ) -> RawConstDef:
        """Adds a constant to a module, backed by a `hugr.val.Value`."""
        module = module or self.get_module()
        type_ast = _parse_expr_string(ty, f"Not a valid Guppy type: `{ty}`")
        defn = RawConstDef(DefId.fresh(module), name, None, type_ast, value)
        module.register_def(defn)
        return defn

    def extern(
        self,
        name: str,
        ty: str,
        symbol: str | None = None,
        constant: bool = True,
        module: GuppyModule | None = None,
    ) -> RawExternDef:
        """Adds an extern symbol to a module."""
        module = module or self.get_module()
        type_ast = _parse_expr_string(ty, f"Not a valid Guppy type: `{ty}`")
        defn = RawExternDef(
            DefId.fresh(module), name, None, symbol or name, constant, type_ast
        )
        module.register_def(defn)
        return defn

    def load(self, m: ModuleType | GuppyModule) -> None:
        caller = self._get_python_caller()
        if caller not in self._modules:
            self._modules[caller] = GuppyModule(caller.name)
        module = self._modules[caller]
        module.load_all(m)

    def get_module(self, id: ModuleIdentifier | None = None, resolve_implicit_imports: bool = True) -> GuppyModule:
        """Returns the local GuppyModule."""
        if id is None:
            id = self._get_python_caller()
        if id not in self._modules:
            self._modules[id] = GuppyModule(id.name.split(".")[-1])
        module = self._modules[id]
        # Update implicit imports
        if resolve_implicit_imports and id.module:
            defs: dict[str, Definition | ModuleType] = {}
            for x, value in id.module.__dict__.items():
                if isinstance(value, Definition):
                    other_module = value.id.module
                    if other_module and other_module != module:
                        defs[x] = value
                elif isinstance(value, ModuleType):
                    try:
                        other_module = find_guppy_module_in_py_module(value)
                        if other_module and other_module != module:
                            defs[x] = value
                    except GuppyError:
                        pass
            module.load(**defs)
        return module

    def compile_module(self, id: ModuleIdentifier | None = None) -> hugr.ext.Package:
        """Compiles the local module into a Hugr."""
        module = self.get_module(id)
        if not module:
            err = (
                f"Module {id.name} not found."
                if id
                else "No Guppy functions or types defined in this module."
            )
            raise MissingModuleError(err)
        return module.compile()

    def registered_modules(self) -> KeysView[ModuleIdentifier]:
        """Returns a list of all currently registered modules for local contexts."""
        return self._modules.keys()


guppy = _Guppy()


def _parse_expr_string(ty_str: str, parse_err: str) -> ast.expr:
    """Helper function to parse expressions that are provided as strings.

    Tries to infer the source location were the given string was defined by inspecting
    the call stack.
    """
    try:
        expr_ast = ast.parse(ty_str, mode="eval").body
    except SyntaxError:
        raise GuppyError(parse_err) from None

    # Try to annotate the type AST with source information. This requires us to
    # inspect the stack frame of the caller
    if caller_frame := _get_calling_frame():
        info = inspect.getframeinfo(caller_frame)
        if caller_module := inspect.getmodule(caller_frame):
            source_lines, _ = inspect.getsourcelines(caller_module)
            source = "".join(source_lines)
            annotate_location(expr_ast, source, info.filename, 0)
            # Modify the AST so that all sub-nodes span the entire line. We
            # can't give a better location since we don't know the column
            # offset of the `ty` argument
            for node in [expr_ast, *ast.walk(expr_ast)]:
                node.lineno, node.col_offset = info.lineno, 0
                node.end_col_offset = len(source_lines[info.lineno - 1])
    return expr_ast


def _get_calling_frame() -> FrameType | None:
    """Finds the first frame that called this function outside the current module."""
    frame = inspect.currentframe()
    while frame:
        module = inspect.getmodule(frame)
        if module is None:
            break
        if module.__file__ != __file__:
            return frame
        frame = frame.f_back
    return None
