import ast
import inspect
import textwrap
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from guppylang.ast_util import AstNode, annotate_location, with_loc
from guppylang.checker.cfg_checker import CheckedCFG
from guppylang.checker.core import Context, Globals, PyScope
from guppylang.checker.expr_checker import check_call, synthesize_call
from guppylang.checker.func_checker import check_global_func_def, check_signature
from guppylang.compiler.core import CompiledGlobals, DFContainer
from guppylang.compiler.expr_compiler import inout_return_ports
from guppylang.compiler.func_compiler import compile_global_func_def
from guppylang.definition.common import CheckableDef, CompilableDef, ParsableDef
from guppylang.definition.value import CallableDef, CompiledCallableDef
from guppylang.error import GuppyError
from guppylang.hugr_builder.hugr import DFContainingVNode, Hugr, Node, OutPortV
from guppylang.nodes import GlobalCall
from guppylang.tys.subst import Inst, Subst
from guppylang.tys.ty import FunctionType, Type

PyFunc = Callable[..., Any]


@dataclass(frozen=True)
class RawFunctionDef(ParsableDef):
    """A raw function definition provided by the user.

    The raw definition stores exactly what the user has written (i.e. the AST), without
    any additional checking or parsing. Furthermore, we store the values of the Python
    variables in scope at the point of definition.
    """

    python_func: PyFunc
    python_scope: PyScope

    description: str = field(default="function", init=False)

    def parse(self, globals: Globals) -> "ParsedFunctionDef":
        """Parses and checks the user-provided signature of the function."""
        func_ast = parse_py_func(self.python_func)
        ty = check_signature(func_ast, globals)
        if ty.parametrized:
            raise GuppyError(
                "Generic function definitions are not supported yet", func_ast
            )
        return ParsedFunctionDef(self.id, self.name, func_ast, ty, self.python_scope)


@dataclass(frozen=True)
class ParsedFunctionDef(CheckableDef, CallableDef):
    """A function definition with parsed and checked signature.

    In particular, this means that we have determined a type for the function and are
    ready to check the function body.
    """

    python_scope: PyScope
    defined_at: ast.FunctionDef
    ty: FunctionType

    description: str = field(default="function", init=False)

    def check(self, globals: Globals) -> "CheckedFunctionDef":
        """Type checks the body of the function."""
        # Add python variable scope to the globals
        globals = globals | Globals({}, {}, {}, self.python_scope)
        cfg = check_global_func_def(self.defined_at, self.ty, globals)
        return CheckedFunctionDef(
            self.id,
            self.name,
            self.defined_at,
            self.ty,
            self.python_scope,
            cfg,
        )

    def check_call(
        self, args: list[ast.expr], ty: Type, node: AstNode, ctx: Context
    ) -> tuple[ast.expr, Subst]:
        """Checks the return type of a function call against a given type."""
        # Use default implementation from the expression checker
        args, subst, inst = check_call(self.ty, args, ty, node, ctx)
        node = with_loc(node, GlobalCall(def_id=self.id, args=args, type_args=inst))
        return node, subst

    def synthesize_call(
        self, args: list[ast.expr], node: AstNode, ctx: Context
    ) -> tuple[ast.expr, Type]:
        """Synthesizes the return type of a function call."""
        # Use default implementation from the expression checker
        args, ty, inst = synthesize_call(self.ty, args, node, ctx)
        node = with_loc(node, GlobalCall(def_id=self.id, args=args, type_args=inst))
        return node, ty


@dataclass(frozen=True)
class CheckedFunctionDef(ParsedFunctionDef, CompilableDef):
    """Type checked version of a user-defined function that is ready to be compiled.

    In particular, this means that we have a constructed and type checked a control-flow
    graph for the function body.
    """

    cfg: CheckedCFG

    def compile_outer(self, graph: Hugr, parent: Node) -> "CompiledFunctionDef":
        """Adds a Hugr `FuncDefn` node for this function to the Hugr.

        Note that we don't compile the function body at this point since we don't have
        access to the other compiled functions yet. The body is compiled later in
        `CompiledFunctionDef.compile_inner()`.
        """
        def_node = graph.add_def(self.ty, parent, self.name)
        return CompiledFunctionDef(
            self.id,
            self.name,
            self.defined_at,
            self.ty,
            self.python_scope,
            self.cfg,
            def_node,
        )


@dataclass(frozen=True)
class CompiledFunctionDef(CheckedFunctionDef, CompiledCallableDef):
    """A function definition with a corresponding Hugr node."""

    hugr_node: DFContainingVNode

    def load_with_args(
        self,
        type_args: Inst,
        dfg: DFContainer,
        graph: Hugr,
        globals: CompiledGlobals,
        node: AstNode,
    ) -> OutPortV:
        """Loads the function as a value into a local Hugr dataflow graph."""
        return graph.add_load_function(
            self.hugr_node.out_port(0), type_args, dfg.node
        ).out_port(0)

    def compile_call(
        self,
        args: list[OutPortV],
        type_args: Inst,
        dfg: DFContainer,
        graph: Hugr,
        globals: CompiledGlobals,
        node: AstNode,
    ) -> tuple[list[OutPortV], list[OutPortV]]:
        """Compiles a call to the function."""
        call = graph.add_call(self.hugr_node.out_port(0), args, type_args, dfg.node)
        return list(call.out_ports), list(inout_return_ports(call, self.ty))

    def compile_inner(self, graph: Hugr, globals: CompiledGlobals) -> None:
        """Compiles the body of the function."""
        compile_global_func_def(self, self.hugr_node, graph, globals)


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
