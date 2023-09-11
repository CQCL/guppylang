import ast
import functools
import inspect
import sys
import textwrap
from dataclasses import dataclass
from types import ModuleType
from typing import Optional, Any, Callable, Union

from guppy.ast_util import is_empty_body
from guppy.compiler_base import Globals
from guppy.extension import GuppyExtension
from guppy.function import FunctionDefCompiler, DefinedFunction
from guppy.hugr.hugr import Hugr
from guppy.error import GuppyError, SourceLoc


def format_source_location(
    source_lines: list[str],
    loc: Union[ast.AST, ast.operator, ast.expr, ast.arg, ast.Name],
    line_offset: int,
    num_lines: int = 3,
    indent: int = 4,
) -> str:
    """Creates a pretty banner to show source locations for errors."""
    assert loc.end_col_offset is not None  # TODO
    s = "".join(source_lines[max(loc.lineno - num_lines, 0) : loc.lineno]).rstrip()
    s += "\n" + loc.col_offset * " " + (loc.end_col_offset - loc.col_offset) * "^"
    s = textwrap.dedent(s).splitlines()
    # Add line numbers
    line_numbers = [
        str(line_offset + loc.lineno - i) + ":" for i in range(num_lines, 0, -1)
    ]
    longest = max(len(ln) for ln in line_numbers)
    prefixes = [ln + " " * (longest - len(ln) + indent) for ln in line_numbers]
    res = ""
    for prefix, line in zip(prefixes, s[:-1]):
        res += prefix + line + "\n"
    res += (longest + indent) * " " + s[-1]
    return res


@dataclass
class RawFunction:
    pyfun: Callable[..., Any]
    ast: ast.FunctionDef
    source_lines: list[str]
    line_offset: int


class GuppyModule(object):
    """A Guppy module backed by a Hugr graph.

    Instances of this class can be used as a decorator to add functions to the module.
    After all functions are added, `compile()` must be called to obtain the Hugr.
    """

    name: str
    globals: Globals

    _func_defs: dict[str, RawFunction]
    _func_decls: dict[str, RawFunction]

    def __init__(self, name: str):
        self.name = name
        self.globals = Globals.default()
        self._func_defs = {}
        self._func_decls = {}

        # Load all prelude extensions
        import guppy.prelude.builtin
        import guppy.prelude.boolean
        import guppy.prelude.float
        import guppy.prelude.integer

        self.load(guppy.prelude.builtin)
        self.load(guppy.prelude.boolean)
        self.load(guppy.prelude.float)
        self.load(guppy.prelude.integer)

    def __call__(self, f: Callable[..., Any]) -> Callable[..., Any]:
        func = self._parse(f)
        self._func_defs[func.ast.name] = func

        @functools.wraps(f)
        def dummy(*args: Any, **kwargs: Any) -> Any:
            raise GuppyError("Guppy functions can only be called in a Guppy context")

        return dummy

    def declare(self, f: Callable[..., Any]) -> None:
        """Decorator to add a function declaration to the module."""
        func = self._parse(f)
        self._func_decls[func.ast.name] = func

    def load(self, m: ModuleType) -> None:
        """Loads a Guppy extension from a python module.

        This function must be called for names from the extension to become available in
        the Guppy.
        """
        for ext in m.__dict__.values():
            if isinstance(ext, GuppyExtension):
                ext.add_to_globals(self.globals)

    def _parse(self, f: Callable[..., Any]) -> RawFunction:
        source_lines, line_offset = inspect.getsourcelines(f)
        line_offset -= 1
        source = "".join(source_lines)  # Lines already have trailing \n's
        source = textwrap.dedent(source)
        func_ast = ast.parse(source).body[0]
        if not isinstance(func_ast, ast.FunctionDef):
            raise GuppyError("Only functions can be placed in modules", func_ast)
        if func_ast.name in self._func_defs:
            raise GuppyError(
                f"Module `{self.name}` already contains a function named `{func_ast.name}` "
                f"(declared at {SourceLoc.from_ast(self._func_defs[func_ast.name].ast, line_offset)})",
                func_ast,
            )
        return RawFunction(f, func_ast, source_lines, line_offset)

    def compile(self, exit_on_error: bool = False) -> Optional[Hugr]:
        """Compiles the module and returns the final Hugr."""
        graph = Hugr(self.name)
        module_node = graph.set_root_name(self.name)
        try:
            # Generate nodes for all function definition and declarations and add them
            # to the globals
            defs = {}
            for name, f in self._func_defs.items():
                func_ty = FunctionDefCompiler.validate_signature(f.ast, self.globals)
                def_node = graph.add_def(func_ty, module_node, f.ast.name)
                defs[name] = def_node
                self.globals.values[name] = DefinedFunction(
                    name, def_node.out_port(0), f.ast
                )
            for name, f in self._func_decls.items():
                func_ty = FunctionDefCompiler.validate_signature(f.ast, self.globals)
                if not is_empty_body(f.ast):
                    raise GuppyError(
                        "Function declarations may not have a body.", f.ast.body[0]
                    )
                decl_node = graph.add_declare(func_ty, module_node, f.ast.name)
                self.globals.values[name] = DefinedFunction(
                    name, decl_node.out_port(0), f.ast
                )

            # Now compile functions definitions
            for name, f in self._func_defs.items():
                FunctionDefCompiler(graph, self.globals).compile_global(
                    f.ast, defs[name]
                )
            return graph

        except GuppyError as err:
            if err.location:
                loc = err.location
                line = f.line_offset + loc.lineno
                print(
                    "Guppy compilation failed. "
                    f"Error in file {inspect.getsourcefile(f.pyfun)}:{line}\n",
                    file=sys.stderr,
                )
                print(
                    format_source_location(f.source_lines, loc, f.line_offset + 1),
                    file=sys.stderr,
                )
            else:
                print(
                    "Guppy compilation failed. "
                    f"Error in file {inspect.getsourcefile(f.pyfun)}\n",
                    file=sys.stderr,
                )
            print(
                f"{err.__class__.__name__}: {err.get_msg(f.line_offset)}",
                file=sys.stderr,
            )
            if exit_on_error:
                sys.exit(1)
            return None


def guppy(f: Callable[..., Any]) -> Optional[Hugr]:
    """Decorator to compile functions outside of modules for testing."""
    module = GuppyModule("module")
    module(f)
    return module.compile(exit_on_error=False)
