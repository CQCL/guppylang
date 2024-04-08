import ast
import inspect
import itertools
import sys
import textwrap
from collections.abc import Callable, Mapping
from types import ModuleType
from typing import Any, Union

from guppylang.ast_util import AstNode, annotate_location
from guppylang.checker.core import Globals, PyScope
from guppylang.compiler.core import CompiledGlobals
from guppylang.definition.common import (
    CheckableDef,
    CheckedDef,
    CompilableDef,
    DefId,
    ParsableDef,
    RawDef,
)
from guppylang.definition.custom import CustomFunctionDef
from guppylang.definition.declaration import RawFunctionDecl
from guppylang.definition.function import RawFunctionDef
from guppylang.definition.parameter import TypeVarDef
from guppylang.error import GuppyError, pretty_errors
from guppylang.hugr.hugr import Hugr
from guppylang.tys.definition import TypeDef

PyFunc = Callable[..., Any]
PyFuncDefOrDecl = tuple[bool, PyFunc]


class GuppyModule:
    """A Guppy module that may contain function and type definitions."""

    name: str

    # Whether the module has already been compiled
    _compiled: bool

    # Map of raw definitions in this module
    _raw_defs: dict[DefId, RawDef]
    _raw_type_defs: dict[DefId, RawDef]

    # Globals from imported modules
    _imported_globals: Globals
    _imported_compiled_globals: CompiledGlobals

    # Globals for functions and types defined in this module. Only gets populated during
    # compilation
    _globals: Globals
    _compiled_globals: CompiledGlobals

    # When `_instance_buffer` is not `None`, then all registered functions will be
    # buffered in this list. They only get properly registered, once
    # `_register_buffered_instance_funcs` is called. This way, we can associate
    _instance_func_buffer: dict[str, RawDef] | None

    def __init__(self, name: str, import_builtins: bool = True):
        self.name = name
        self._globals = Globals({}, {}, {}, {})
        self._compiled_globals = {}
        self._imported_globals = Globals.default()
        self._imported_compiled_globals = {}
        self._compiled = False
        self._instance_func_buffer = None
        self._raw_defs = {}
        self._raw_type_defs = {}

        # Import builtin module
        if import_builtins:
            import guppylang.prelude.builtins as builtins

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
                not isinstance(v, CustomFunctionDef | TypeDef | TypeVarDef)
                for v in m._compiled_globals.values()
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

    def register_def(self, defn: RawDef, instance: TypeDef | None = None) -> None:
        """Registers a definition with this module.

        Optionally, the definition can be marked as an instance method by passing the
        corresponding instance type definition.
        """
        self._check_not_yet_compiled()
        if self._instance_func_buffer is not None and not isinstance(defn, TypeDef):
            self._instance_func_buffer[defn.name] = defn
        else:
            self._check_name_available(defn.name, defn.defined_at)
            if isinstance(defn, TypeDef):
                self._raw_type_defs[defn.id] = defn
            else:
                self._raw_defs[defn.id] = defn
            if instance is not None:
                self._globals.impls.setdefault(instance.id, {})
                self._globals.impls[instance.id][defn.name] = defn.id
            else:
                self._globals.names[defn.name] = defn.id

    def register_func_def(
        self, f: PyFunc, instance: TypeDef | None = None
    ) -> RawFunctionDef:
        """Registers a Python function definition as belonging to this Guppy module."""
        func_ast = parse_py_func(f)
        defn = RawFunctionDef(
            DefId.fresh(self), func_ast.name, func_ast, get_py_scope(f)
        )
        self.register_def(defn, instance)
        return defn

    def register_func_decl(
        self, f: PyFunc, instance: TypeDef | None = None
    ) -> RawFunctionDecl:
        """Registers a Python function declaration as belonging to this Guppy module."""
        func_ast = parse_py_func(f)
        decl = RawFunctionDecl(DefId.fresh(self), func_ast.name, func_ast)
        self.register_def(decl, instance)
        return decl

    def _register_buffered_instance_funcs(self, instance: TypeDef) -> None:
        assert self._instance_func_buffer is not None
        buffer = self._instance_func_buffer
        self._instance_func_buffer = None
        for defn in buffer.values():
            self.register_def(defn, instance)

    @property
    def compiled(self) -> bool:
        return self._compiled

    @staticmethod
    def _check_defs(
        raw_defs: Mapping[DefId, RawDef], globals: Globals
    ) -> dict[DefId, CheckedDef]:
        """Helper method to parse and check raw definitions."""
        raw_globals = globals | Globals(raw_defs, {}, {}, {})
        parsed = {
            defn.id: defn.parse(raw_globals) if isinstance(defn, ParsableDef) else defn
            for defn in raw_defs.values()
        }
        parsed_globals = globals | Globals(parsed, {}, {}, {})
        return {
            defn.id: (
                defn.check(parsed_globals) if isinstance(defn, CheckableDef) else defn
            )
            for defn in parsed.values()
        }

    @pretty_errors
    def compile(self) -> Hugr | None:
        """Compiles the module and returns the final Hugr."""
        if self.compiled:
            raise GuppyError("Module has already been compiled")

        # Type definitions need to be checked first so that we can use them when parsing
        # function signatures etc.
        type_defs = self._check_defs(
            self._raw_type_defs, self._imported_globals | self._globals
        )
        self._globals = self._globals.update_defs(type_defs)

        # Now, we can check all other definitions
        other_defs = self._check_defs(
            self._raw_defs, self._imported_globals | self._globals
        )
        self._globals = self._globals.update_defs(other_defs)

        # Prepare Hugr for this module
        graph = Hugr(self.name)
        module_node = graph.set_root_name(self.name)

        # Compile definitions to Hugr
        self._compiled_globals = {
            defn.id: (
                defn.compile(graph, module_node)
                if isinstance(defn, CompilableDef)
                else defn
            )
            for defn in itertools.chain(type_defs.values(), other_defs.values())
        }
        all_compiled_globals = self._compiled_globals | self._imported_compiled_globals

        # Finally, compile the definition contents to Hugr. For example, this compiles
        # the bodies of functions.
        for defn in self._compiled_globals.values():
            defn.compile_contents(graph, all_compiled_globals)

        self._compiled = True
        return graph

    def contains(self, name: str) -> bool:
        """Returns 'True' if the module contains an object with the given name."""
        return name in self._globals.names

    def _check_not_yet_compiled(self) -> None:
        if self._compiled:
            raise GuppyError(f"The module `{self.name}` has already been compiled")

    def _check_name_available(self, name: str, node: AstNode | None) -> None:
        if self.contains(name):
            raise GuppyError(
                f"Module `{self.name}` already contains a definition named `{name}`",
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


def get_py_scope(f: PyFunc) -> PyScope:
    """Returns a mapping of all variables captured by a Python function.

    Note that this function only works in CPython. On other platforms, an empty
    dictionary is returned.

    Relies on inspecting the `__globals__` and `__closure__` attributes of the function.
    See https://docs.python.org/3/reference/datamodel.html#special-read-only-attributes
    """
    if sys.implementation.name != "cpython":
        return {}

    if inspect.ismethod(f):
        f = f.__func__
    code = f.__code__

    nonlocals: PyScope = {}
    if f.__closure__ is not None:
        for var, cell in zip(code.co_freevars, f.__closure__):
            try:
                value = cell.cell_contents
            except ValueError:
                # The call to `cell_contents` will fail if `var` is a recursive
                # reference to the decorated function
                continue
            nonlocals[var] = value

    return nonlocals | f.__globals__.copy()
