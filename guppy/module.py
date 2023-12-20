import ast
import inspect
import textwrap
from collections.abc import Callable
from types import ModuleType
from typing import Any, Union

from guppy.ast_util import AstNode, annotate_location
from guppy.checker.core import Globals, TypeVarDecl, qualified_name
from guppy.checker.func_checker import DefinedFunction, check_global_func_def
from guppy.compiler.core import CompiledGlobals
from guppy.compiler.func_compiler import CompiledFunctionDef, compile_global_func_def
from guppy.custom import CustomFunction
from guppy.declared import DeclaredFunction
from guppy.error import GuppyError, pretty_errors
from guppy.gtypes import GuppyType
from guppy.hugr.hugr import Hugr

PyFunc = Callable[..., Any]
PyFuncDefOrDecl = tuple[bool, PyFunc]


class GuppyModule:
    """A Guppy module that may contain function and type definitions."""

    name: str

    # Whether the module has already been compiled
    _compiled: bool

    # Globals from imported modules
    _imported_globals: Globals
    _imported_compiled_globals: CompiledGlobals

    # Globals for functions and types defined in this module. Only gets populated during
    # compilation
    _globals: Globals
    _compiled_globals: CompiledGlobals

    # Mappings of functions defined in this module
    _func_defs: dict[str, ast.FunctionDef]
    _func_decls: dict[str, ast.FunctionDef]
    _custom_funcs: dict[str, CustomFunction]

    # When `_instance_buffer` is not `None`, then all registered functions will be
    # buffered in this list. They only get properly registered, once
    # `_register_buffered_instance_funcs` is called. This way, we can associate
    _instance_func_buffer: dict[str, PyFuncDefOrDecl | CustomFunction] | None

    def __init__(self, name: str, import_builtins: bool = True):
        self.name = name
        self._globals = Globals({}, {}, {})
        self._compiled_globals = {}
        self._imported_globals = Globals.default()
        self._imported_compiled_globals = {}
        self._func_defs = {}
        self._func_decls = {}
        self._custom_funcs = {}
        self._compiled = False
        self._instance_func_buffer = None

        # Import builtin module
        if import_builtins:
            import guppy.prelude.builtins as builtins

            self.load(builtins)

    def load(self, m: Union[ModuleType, "GuppyModule"]) -> None:
        """Imports another Guppy module."""
        self._check_not_yet_compiled()
        if isinstance(m, GuppyModule):
            # Compile module if it isn't compiled yet
            if not m.compiled:
                m.compile()

            # For now, we can only import custom functions
            if any(
                not isinstance(v, CustomFunction) for v in m._compiled_globals.values()
            ):
                raise GuppyError(
                    "Importing modules with defined functions is not supported yet"
                )

            self._imported_globals |= m._globals
            self._imported_compiled_globals |= m._compiled_globals
        else:
            for val in m.__dict__.values():
                if isinstance(val, GuppyModule):
                    self.load(val)

    def register_func_def(
        self, f: PyFunc, instance: type[GuppyType] | None = None
    ) -> None:
        """Registers a Python function definition as belonging to this Guppy module."""
        self._check_not_yet_compiled()
        func_ast = parse_py_func(f)
        if self._instance_func_buffer is not None:
            self._instance_func_buffer[func_ast.name] = (True, f)
        else:
            name = (
                qualified_name(instance, func_ast.name) if instance else func_ast.name
            )
            self._check_name_available(name, func_ast)
            self._func_defs[name] = func_ast

    def register_func_decl(
        self, f: PyFunc, instance: type[GuppyType] | None = None
    ) -> None:
        """Registers a Python function declaration as belonging to this Guppy module."""
        self._check_not_yet_compiled()
        func_ast = parse_py_func(f)
        if self._instance_func_buffer is not None:
            self._instance_func_buffer[func_ast.name] = (False, f)
        else:
            name = (
                qualified_name(instance, func_ast.name) if instance else func_ast.name
            )
            self._check_name_available(name, func_ast)
            self._func_decls[name] = func_ast

    def register_custom_func(
        self, func: CustomFunction, instance: type[GuppyType] | None = None
    ) -> None:
        """Registers a custom function as belonging to this Guppy module."""
        self._check_not_yet_compiled()
        if self._instance_func_buffer is not None:
            self._instance_func_buffer[func.name] = func
        else:
            if instance:
                func.name = qualified_name(instance, func.name)
            self._check_name_available(func.name, func.defined_at)
            self._custom_funcs[func.name] = func

    def register_type(self, name: str, ty: type[GuppyType]) -> None:
        """Registers an existing Guppy type as belonging to this Guppy module."""
        self._check_not_yet_compiled()
        self._check_type_name_available(name, None)
        self._globals.types[name] = ty

    def register_type_var(self, name: str, linear: bool) -> None:
        """Registers a new type variable"""
        self._check_not_yet_compiled()
        self._check_type_name_available(name, None)
        self._globals.type_vars[name] = TypeVarDecl(name, linear)

    def _register_buffered_instance_funcs(self, instance: type[GuppyType]) -> None:
        assert self._instance_func_buffer is not None
        buffer = self._instance_func_buffer
        self._instance_func_buffer = None
        for f in buffer.values():
            if isinstance(f, CustomFunction):
                self.register_custom_func(f, instance)
            else:
                is_def, pyfunc = f
                if is_def:
                    self.register_func_def(pyfunc, instance)
                else:
                    self.register_func_decl(pyfunc, instance)

    @property
    def compiled(self) -> bool:
        return self._compiled

    @pretty_errors
    def compile(self) -> Hugr | None:
        """Compiles the module and returns the final Hugr."""
        if self.compiled:
            raise GuppyError("Module has already been compiled")

        # Prepare globals for type checking
        for func in self._custom_funcs.values():
            func.check_type(self._imported_globals | self._globals)
        defined_funcs = {
            x: DefinedFunction.from_ast(f, x, self._imported_globals | self._globals)
            for x, f in self._func_defs.items()
        }
        declared_funcs = {
            x: DeclaredFunction.from_ast(f, x, self._imported_globals | self._globals)
            for x, f in self._func_decls.items()
        }
        self._globals.values.update(self._custom_funcs)
        self._globals.values.update(declared_funcs)
        self._globals.values.update(defined_funcs)

        # Type check function definitions
        checked = {
            x: check_global_func_def(f, self._imported_globals | self._globals)
            for x, f in defined_funcs.items()
        }

        # Add declared functions to the graph
        graph = Hugr(self.name)
        module_node = graph.set_root_name(self.name)
        for f in declared_funcs.values():
            f.add_to_graph(graph, module_node)

        # Prepare `FunctionDef` nodes for all function definitions
        def_nodes = {x: graph.add_def(f.ty, module_node, x) for x, f in checked.items()}
        self._compiled_globals |= (
            self._custom_funcs
            | declared_funcs
            | {
                x: CompiledFunctionDef(x, f.ty, f.defined_at, None, def_nodes[x])
                for x, f in checked.items()
            }
        )

        # Compile function definitions to Hugr
        for x, f in checked.items():
            compile_global_func_def(
                f,
                def_nodes[x],
                graph,
                self._imported_compiled_globals | self._compiled_globals,
            )

        self._compiled = True
        return graph

    def _check_not_yet_compiled(self) -> None:
        if self._compiled:
            raise GuppyError(f"The module `{self.name}` has already been compiled")

    def _check_name_available(self, name: str, node: AstNode | None) -> None:
        if name in self._func_defs or name in self._custom_funcs:
            raise GuppyError(
                f"Module `{self.name}` already contains a function named `{name}`",
                node,
            )

    def _check_type_name_available(self, name: str, node: AstNode | None) -> None:
        if name in self._globals.types:
            raise GuppyError(
                f"Module `{self.name}` already contains a type `{name}`",
                node,
            )

        if name in self._globals.type_vars:
            raise GuppyError(
                f"Module `{self.name}` already contains a type variable `{name}`",
                node,
            )


def parse_py_func(f: PyFunc) -> ast.FunctionDef:
    source_lines, line_offset = inspect.getsourcelines(f)
    source = "".join(source_lines)  # Lines already have trailing \n's
    source = textwrap.dedent(source)
    func_ast = ast.parse(source).body[0]
    file = inspect.getsourcefile(f)
    if file is None:
        raise GuppyError("Couldn't determine source file for function")
    annotate_location(func_ast, source, file, line_offset)
    if not isinstance(func_ast, ast.FunctionDef):
        raise GuppyError("Expected a function definition", func_ast)
    return func_ast
