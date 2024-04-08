import inspect
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, TypeVar

from guppylang.ast_util import has_empty_body
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
from guppylang.definition.function import RawFunctionDef
from guppylang.definition.parameter import TypeVarDef
from guppylang.error import GuppyError, MissingModuleError, pretty_errors
from guppylang.hugr import ops, tys
from guppylang.hugr.hugr import Hugr
from guppylang.module import GuppyModule, PyFunc, parse_py_func
from guppylang.tys.definition import OpaqueTypeDef, TypeDef

FuncDefDecorator = Callable[[PyFunc], RawFunctionDef]
FuncDeclDecorator = Callable[[PyFunc], RawFunctionDecl]
CustomFuncDecorator = Callable[[PyFunc], RawCustomFunctionDef]
ClassDecorator = Callable[[type], type]


@dataclass(frozen=True)
class ModuleIdentifier:
    """Identifier for the Python file/module that called the decorator."""

    filename: Path
    module: ModuleType | None

    @property
    def name(self) -> str:
        """Returns a user-friendly name for the caller.

        If the called is not a function, uses the file name.
        """
        if self.module is not None:
            return str(self.module.__name__)
        return self.filename.name


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
        return ModuleIdentifier(Path(filename), module)

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
        hugr_ty: tys.Type,
        name: str = "",
        linear: bool = False,
        bound: tys.TypeBound | None = None,
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
    def type_var(self, module: GuppyModule, name: str, linear: bool = False) -> TypeVar:
        """Creates a new type variable in a module."""
        defn = TypeVarDef(DefId.fresh(module), name, None, linear)
        module.register_def(defn)
        # Return an actual Python `TypeVar` so it can be used as an actual type in code
        # that is executed by interpreter before handing it to Guppy.
        return TypeVar(name)

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
            func_ast = parse_py_func(f)
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
        op: ops.OpType,
        checker: CustomCallChecker | None = None,
        higher_order_value: bool = True,
        name: str = "",
    ) -> CustomFuncDecorator:
        """Decorator to annotate function declarations as HUGR ops."""
        return self.custom(module, OpCompiler(op), checker, higher_order_value, name)

    def declare(self, module: GuppyModule) -> FuncDeclDecorator:
        """Decorator to declare functions"""

        def dec(f: Callable[..., Any]) -> RawFunctionDecl:
            return module.register_func_decl(f)

        return dec

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

    def compile_module(self, id: ModuleIdentifier | None = None) -> Hugr | None:
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
