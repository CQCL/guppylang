import ast
import inspect
import sys
import textwrap
from dataclasses import dataclass
from typing import Optional, Any, Callable, Union

from guppy.cfg import CFGBuilder
from guppy.compiler_base import CompilerBase, VarMap, RawVariable, Variable
from guppy.expression import expr_to_row
from guppy.guppy_types import (
    GuppyType,
    IntType,
    FloatType,
    BoolType,
    FunctionType,
    TupleType,
    TypeRow,
    StringType, QubitType,
)
from guppy.hugr.hugr import Hugr, Node
from guppy.error import GuppyError, SourceLoc


def type_from_ast(node: ast.expr) -> GuppyType:
    """Turns an AST expression into a Guppy type."""
    if isinstance(node, ast.Name):
        if node.id == "int":
            return IntType()
        elif node.id == "float":
            return FloatType()
        elif node.id == "bool":
            return BoolType()
        elif node.id == "str":
            return StringType()
        elif node.id == "qubit":
            return QubitType()
    elif isinstance(node, ast.Tuple):
        return TupleType([type_from_ast(el) for el in node.elts])
    # TODO: Remaining cases
    raise GuppyError(f"Invalid type: `{ast.unparse(node)}`", node)


def type_row_from_ast(node: ast.expr) -> TypeRow:
    """Turns an AST expression into a Guppy type row.

    This is needed to interpret the return type annotation of functions.
    """
    # The return type `-> None` is represented in the ast as `ast.Constant(value=None)`
    if isinstance(node, ast.Constant) and node.value is None:
        return TypeRow([])
    return TypeRow([type_from_ast(e) for e in expr_to_row(node)])


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


class FunctionCompiler(CompilerBase):
    cfg_builder: CFGBuilder

    def __init__(self, graph: Hugr):
        self.graph = graph
        self.cfg_builder = CFGBuilder()

    @staticmethod
    def validate_signature(func_def: ast.FunctionDef) -> FunctionType:
        """Checks the signature of a function definition and returns the corresponding
        Guppy type."""
        if len(func_def.args.posonlyargs) != 0:
            raise GuppyError(
                "Positional-only parameters not supported", func_def.args.posonlyargs[0]
            )
        if len(func_def.args.kwonlyargs) != 0:
            raise GuppyError(
                "Keyword-only parameters not supported", func_def.args.kwonlyargs[0]
            )
        if func_def.args.vararg is not None:
            raise GuppyError("*args not supported", func_def.args.vararg)
        if func_def.args.kwarg is not None:
            raise GuppyError("**kwargs not supported", func_def.args.kwarg)
        if func_def.returns is None:
            raise GuppyError(
                "Return type must be annotated", func_def
            )  # TODO: Error location is incorrect

        arg_tys = []
        arg_names = []
        for i, arg in enumerate(func_def.args.args):
            if arg.annotation is None:
                raise GuppyError("Argument type must be annotated", arg)
            ty = type_from_ast(arg.annotation)
            arg_tys.append(ty)
            arg_names.append(arg.arg)

        ret_type_row = type_row_from_ast(func_def.returns)
        return FunctionType(arg_tys, ret_type_row.tys, arg_names)

    def compile(
        self,
        module: "GuppyModule",
        func_def: ast.FunctionDef,
        def_node: Node,
        global_variables: VarMap,
    ) -> GuppyFunction:
        self.global_variables = global_variables
        func_ty = self.validate_signature(func_def)
        args = func_def.args.args

        cfg = self.cfg_builder.build(func_def.body, len(func_ty.returns))
        cfg.analyze()

        def_input = self.graph.add_input(parent=def_node)
        cfg_node = self.graph.add_cfg(
            def_node, inputs=[def_input.add_out_port(ty) for ty in func_ty.args]
        )
        assert func_ty.arg_names is not None
        input_sig = [
            RawVariable(x, t, {l})
            for x, t, l in zip(func_ty.arg_names, func_ty.args, args)
        ]
        cfg.compile(
            self.graph, input_sig, list(func_ty.returns), cfg_node, global_variables
        )

        # Add final output node for the def block
        self.graph.add_output(
            inputs=[cfg_node.add_out_port(ty) for ty in func_ty.returns],
            parent=def_node,
        )

        return GuppyFunction(func_def.name, module, def_node, func_ty, func_def)


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


class GuppyModule(object):
    """A Guppy module backed by a Hugr graph.

    Instances of this class can be used as a decorator to add functions to the module.
    After all functions are added, `compile()` must be called to obtain the Hugr.
    """

    name: str
    graph: Hugr
    module_node: Node
    compiler: FunctionCompiler
    # function, AST, source lines, line offset
    annotated_funcs: dict[
        str, tuple[Callable[..., Any], ast.FunctionDef, list[str], int]
    ]
    fun_decls: list[GuppyFunction]

    def __init__(self, name: str):
        self.name = name
        self.graph = Hugr(name)
        self.module_node = self.graph.set_root_name(self.name)
        self.compiler = FunctionCompiler(self.graph)
        self.annotated_funcs = {}
        self.fun_decls = []

    def __call__(self, f: Callable[..., Any]) -> None:
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
                f"(declared at {SourceLoc.from_ast(self.annotated_funcs[func_ast.name][1], line_offset)})",
                func_ast,
            )
        self.annotated_funcs[func_ast.name] = f, func_ast, source_lines, line_offset

    def compile(self, exit_on_error: bool = False) -> Optional[Hugr]:
        """Compiles the module and returns the final Hugr."""
        try:
            global_variables = {}
            defs = {}
            for name, (
                f,
                func_ast,
                source_lines,
                line_offset,
            ) in self.annotated_funcs.items():
                func_ty = self.compiler.validate_signature(func_ast)
                def_node = self.graph.add_def(func_ty, self.module_node, func_ast.name)
                defs[name] = def_node
                global_variables[name] = Variable(
                    name, def_node.out_port(0), {func_ast}
                )
            for name, (
                f,
                func_ast,
                source_lines,
                line_offset,
            ) in self.annotated_funcs.items():
                func = self.compiler.compile(
                    self, func_ast, defs[name], global_variables
                )
                self.fun_decls.append(func)
            return self.graph
        except GuppyError as err:
            if err.location:
                loc = err.location
                line = line_offset + loc.lineno
                print(
                    f"Guppy compilation failed. Error in file {inspect.getsourcefile(f)}:{line}\n",
                    file=sys.stderr,
                )
                print(
                    format_source_location(source_lines, loc, line_offset + 1),
                    file=sys.stderr,
                )
            else:
                print(
                    f'Guppy compilation failed. Error in file "{inspect.getsourcefile(f)}"\n',
                    file=sys.stderr,
                )
            print(
                f"{err.__class__.__name__}: {err.get_msg(line_offset)}", file=sys.stderr
            )
            if exit_on_error:
                sys.exit(1)
            return None


def guppy(f: Callable[..., Any]) -> Optional[Hugr]:
    """Decorator to compile functions outside of modules for testing."""
    module = GuppyModule("module")
    module(f)
    return module.compile(exit_on_error=False)
