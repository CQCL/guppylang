import ast
import inspect
import sys
import textwrap
from dataclasses import dataclass
from typing import Optional, Any, Callable, Union

from guppy.compiler_base import Variable
from guppy.function import FunctionCompiler
from guppy.guppy_types import FunctionType
from guppy.hugr.hugr import Hugr, Node
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


@dataclass
class GuppyFunction:
    """Class holding all information associated with a Function during compilation."""

    name: str
    module: "GuppyModule"
    def_node: Node
    ty: FunctionType
    ast: ast.FunctionDef

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        # The `@guppy` annotator returns a `GuppyFunction`. If the user tries to call
        # it, we can give a nice error message:
        raise GuppyError("Guppy functions can only be called inside of Guppy functions")


class GuppyModule(object):
    """A Guppy module backed by a Hugr graph.

    Instances of this class can be used as a decorator to add functions to the module.
    After all functions are added, `compile()` must be called to obtain the Hugr.
    """

    name: str
    graph: Hugr
    module_node: Node
    compiler: FunctionCompiler
    annotated_funcs: dict[str, RawFunction]
    declared_funcs: dict[str, RawFunction]
    fun_decls: list[GuppyFunction]

    def __init__(self, name: str):
        self.name = name
        self.graph = Hugr(name)
        self.module_node = self.graph.set_root_name(self.name)
        self.annotated_funcs = {}
        self.declared_funcs = {}
        self.fun_decls = []

    def __call__(self, f: Callable[..., Any]) -> None:
        func = self._parse(f)
        self.annotated_funcs[func.ast.name] = func

    def declare(self, f: Callable[..., Any]) -> None:
        func = self._parse(f)
        self.declared_funcs[func.ast.name] = func

    def _parse(self, f: Callable[..., Any]) -> RawFunction:
        source_lines, line_offset = inspect.getsourcelines(f)
        line_offset -= 1
        source = "".join(source_lines)  # Lines already have trailing \n's
        source = textwrap.dedent(source)
        func_ast = ast.parse(source).body[0]
        if not isinstance(func_ast, ast.FunctionDef):
            raise GuppyError("Only functions can be placed in modules", func_ast)
        if func_ast.name in self.annotated_funcs:
            raise GuppyError(
                f"Module `{self.name}` already contains a function named `{func_ast.name}` "
                f"(declared at {SourceLoc.from_ast(self.annotated_funcs[func_ast.name].ast, line_offset)})",
                func_ast,
            )
        return RawFunction(f, func_ast, source_lines, line_offset)

    def compile(self, exit_on_error: bool = False) -> Optional[Hugr]:
        """Compiles the module and returns the final Hugr."""
        try:
            global_variables = {}
            defs = {}
            for name, f in self.annotated_funcs.items():
                func_ty = FunctionCompiler.validate_signature(f.ast)
                def_node = self.graph.add_def(func_ty, self.module_node, f.ast.name)
                defs[name] = def_node
                global_variables[name] = Variable(name, def_node.out_port(0), f.ast)
            for name, f in self.declared_funcs.items():
                func_ty = FunctionCompiler.validate_signature(f.ast)
                if len(f.ast.body) > 1 or not isinstance(f.ast.body[0], ast.Pass):
                    raise GuppyError(
                        "Function declarations may not have a body.", f.ast.body[0]
                    )
                decl_node = self.graph.add_declare(
                    func_ty, self.module_node, f.ast.name
                )
                global_variables[name] = Variable(name, decl_node.out_port(0), f.ast)
            for name, f in self.annotated_funcs.items():
                port = FunctionCompiler(self.graph, global_variables).compile_global(
                    f.ast, defs[name], global_variables
                )
                assert isinstance(port.ty, FunctionType)
                self.fun_decls.append(
                    GuppyFunction(name, self, port.node, port.ty, f.ast)
                )
            return self.graph
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
