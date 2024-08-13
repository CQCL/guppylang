import ast
import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, TypeVar

from hugr import Hugr, ops
from hugr import tys as ht
from hugr.ops import DataflowOp

from guppylang.ast_util import annotate_location, has_empty_body
from guppylang.definition.common import DefId
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
from guppylang.module import GuppyModule, PyFunc
from guppylang.tys.subst import Inst
from guppylang.tys.ty import NumericType

FuncDefDecorator = Callable[[PyFunc], RawFunctionDef]
FuncDeclDecorator = Callable[[PyFunc], RawFunctionDecl]
CustomFuncDecorator = Callable[[PyFunc], RawCustomFunctionDef]
ClassDecorator = Callable[[type], type]
StructDecorator = Callable[[type], RawStructDef]


@dataclass(frozen=True)
class ModuleIdentifier:
    """Identifier for the Python file/module that called the decorator."""

    filename: Path

    #: The name of the module. We only store this to have nice name to report back to
    #: the user. When determining whether two `ModuleIdentifier`s correspond to the same
    #: module, we only take the module path into account.
    name: str = field(compare=False)


class _Guppy:
    """Class for the `@guppy` decorator."""

    # The currently-alive GuppyModules, associated with a Python file/module.
    #
    # Only contains **uncompiled** modules.
    _modules: dict[ModuleIdentifier, GuppyModule]

    def __init__(self) -> None:
        self._modules = {}

    @pretty_errors
    def __call__(self, arg: PyFunc | GuppyModule) -> FuncDefDecorator | RawFunctionDef:
        """Decorator to annotate Python functions as Guppy code.

        Optionally, the `GuppyModule` in which the function should be placed can
        be passed to the decorator.
        """
        if not isinstance(arg, GuppyModule):
            # Decorator used without any arguments.
            # We default to a module associated with the caller of the decorator.
            f = arg

            caller = self._get_python_caller(f)
            if caller not in self._modules:
                self._modules[caller] = GuppyModule(caller.name)
            module = self._modules[caller]
            return module.register_func_def(f)

        if isinstance(arg, GuppyModule):
            # Module passed.
            def dec(f: Callable[..., Any]) -> RawFunctionDef:
                return arg.register_func_def(f)

            return dec

        raise ValueError(f"Invalid arguments to `@guppy` decorator: {arg}")

    def _get_python_caller(self, fn: PyFunc | None = None) -> ModuleIdentifier:
        """Returns an identifier for the Python file/module that called the decorator.

        :param fn: Optional. The function that was decorated.
        """
        if fn is not None:
            filename = inspect.getfile(fn)
            module = inspect.getmodule(fn)
        else:
            for s in inspect.stack():
                if s.filename != __file__:
                    filename = s.filename
                    module = inspect.getmodule(s.frame)
                    break
            else:
                raise GuppyError("Could not find a caller for the `@guppy` decorator")
        module_path = Path(filename)
        return ModuleIdentifier(
            module_path, module.__name__ if module else module_path.name
        )

    @pretty_errors
    def extend_type(self, module: GuppyModule, defn: TypeDef) -> ClassDecorator:
        """Decorator to add new instance functions to a type."""
        module._instance_func_buffer = {}

        def dec(c: type) -> type:
            module._register_buffered_instance_funcs(defn)
            return c

        return dec

    @pretty_errors
    def type(
        self,
        module: GuppyModule,
        hugr_ty: ht.Type,
        name: str = "",
        linear: bool = False,
        bound: ht.TypeBound | None = None,
    ) -> ClassDecorator:
        """Decorator to annotate a class definitions as Guppy types.

        Requires the static Hugr translation of the type. Additionally, the type can be
        marked as linear. All `@guppy` annotated functions on the class are turned into
        instance functions.
        """
        module._instance_func_buffer = {}

        def dec(c: type) -> type:
            defn = OpaqueTypeDef(
                DefId.fresh(module),
                name or c.__name__,
                None,
                [],
                linear,
                lambda _: hugr_ty,
                bound,
            )
            module.register_def(defn)
            module._register_buffered_instance_funcs(defn)
            return c

        return dec

    @pretty_errors
    def struct(self, module: GuppyModule) -> StructDecorator:
        """Decorator to define a new struct."""
        module._instance_func_buffer = {}

        def dec(cls: type) -> RawStructDef:
            defn = RawStructDef(DefId.fresh(module), cls.__name__, None, cls)
            module.register_def(defn)
            module._register_buffered_instance_funcs(defn)
            return defn

        return dec

    @pretty_errors
    def type_var(self, module: GuppyModule, name: str, linear: bool = False) -> TypeVar:
        """Creates a new type variable in a module."""
        defn = TypeVarDef(DefId.fresh(module), name, None, linear)
        module.register_def(defn)
        # Return an actual Python `TypeVar` so it can be used as an actual type in code
        # that is executed by interpreter before handing it to Guppy.
        return TypeVar(name)

    @pretty_errors
    def nat_var(self, module: GuppyModule, name: str) -> ConstVarDef:
        """Creates a new const nat variable in a module."""
        defn = ConstVarDef(
            DefId.fresh(module), name, None, NumericType(NumericType.Kind.Nat)
        )
        module.register_def(defn)
        return defn

    @pretty_errors
    def custom(
        self,
        module: GuppyModule,
        compiler: CustomCallCompiler | None = None,
        checker: CustomCallChecker | None = None,
        higher_order_value: bool = True,
        name: str = "",
    ) -> CustomFuncDecorator:
        """Decorator to add custom typing or compilation behaviour to function decls.

        Optionally, usage of the function as a higher-order value can be disabled. In
        that case, the function signature can be omitted if a custom call compiler is
        provided.
        """

        def dec(f: PyFunc) -> RawCustomFunctionDef:
            func_ast, docstring = parse_py_func(f)
            if not has_empty_body(func_ast):
                raise GuppyError(
                    "Body of custom function declaration must be empty",
                    func_ast.body[0],
                )
            call_checker = checker or DefaultCallChecker()
            func = RawCustomFunctionDef(
                DefId.fresh(module),
                name or func_ast.name,
                func_ast,
                call_checker,
                compiler or NotImplementedCallCompiler(),
                higher_order_value,
            )
            module.register_def(func)
            return func

        return dec

    def hugr_op(
        self,
        module: GuppyModule,
        op: Callable[[Inst], DataflowOp],
        checker: CustomCallChecker | None = None,
        higher_order_value: bool = True,
        name: str = "",
    ) -> CustomFuncDecorator:
        """Decorator to annotate function declarations as HUGR ops.

        Args:
            module: The module in which the function should be defined.
            op: A function that takes an instantiation of the type arguments and returns
                a concrete HUGR op.
            checker: The custom call checker.
            higher_order_value: Whether the function may be used as a higher-order
                value.
            name: The name of the function.
        """
        return self.custom(module, OpCompiler(op), checker, higher_order_value, name)

    def declare(self, module: GuppyModule) -> FuncDeclDecorator:
        """Decorator to declare functions"""

        def dec(f: Callable[..., Any]) -> RawFunctionDecl:
            return module.register_func_decl(f)

        return dec

    def extern(
        self,
        module: GuppyModule,
        name: str,
        ty: str,
        symbol: str | None = None,
        constant: bool = True,
    ) -> RawExternDef:
        """Adds an extern symbol to a module."""
        try:
            type_ast = ast.parse(ty, mode="eval").body
        except SyntaxError:
            err = f"Not a valid Guppy type: `{ty}`"
            raise GuppyError(err) from None

        # Try to annotate the type AST with source information. This requires us to
        # inspect the stack frame of the caller
        if frame := inspect.currentframe():  # noqa: SIM102
            if caller_frame := frame.f_back:  # noqa: SIM102
                if caller_module := inspect.getmodule(caller_frame):
                    info = inspect.getframeinfo(caller_frame)
                    source_lines, _ = inspect.getsourcelines(caller_module)
                    source = "".join(source_lines)
                    annotate_location(type_ast, source, info.filename, 0)
                    # Modify the AST so that all sub-nodes span the entire line. We
                    # can't give a better location since we don't know the column
                    # offset of the `ty` argument
                    for node in [type_ast, *ast.walk(type_ast)]:
                        node.lineno, node.col_offset = info.lineno, 0
                        node.end_col_offset = len(source_lines[info.lineno - 1])

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
        module.load(m)

    def take_module(self, id: ModuleIdentifier | None = None) -> GuppyModule:
        """Returns the local GuppyModule, removing it from the local state."""
        orig_id = id
        if id is None:
            id = self._get_python_caller()
        if id not in self._modules:
            err = (
                f"Module {orig_id.name} not found."
                if orig_id
                else "No Guppy functions or types defined in this module."
            )
            raise MissingModuleError(err)
        return self._modules.pop(id)

    def compile_module(self, id: ModuleIdentifier | None = None) -> Hugr[ops.Module]:
        """Compiles the local module into a Hugr."""
        module = self.take_module(id)
        if not module:
            err = (
                f"Module {id.name} not found."
                if id
                else "No Guppy functions or types defined in this module."
            )
            raise MissingModuleError(err)
        return module.compile()

    def registered_modules(self) -> list[ModuleIdentifier]:
        """Returns a list of all currently registered modules for local contexts."""
        return list(self._modules.keys())


guppy = _Guppy()
