import ast
from dataclasses import dataclass, field

from guppylang.ast_util import AstNode, has_empty_body, with_loc
from guppylang.checker.core import Context, Globals
from guppylang.checker.expr_checker import check_call, synthesize_call
from guppylang.checker.func_checker import check_signature
from guppylang.compiler.core import CompiledGlobals, DFContainer
from guppylang.definition.common import CompilableDef, ParsableDef
from guppylang.definition.function import PyFunc, parse_py_func
from guppylang.definition.value import CallableDef, CompiledCallableDef
from guppylang.error import GuppyError
from guppylang.hugr.hugr import Hugr, Node, OutPortV, VNode
from guppylang.nodes import GlobalCall
from guppylang.tys.subst import Inst, Subst
from guppylang.tys.ty import Type, type_to_row


@dataclass(frozen=True)
class RawFunctionDecl(ParsableDef):
    """A raw function declaration provided by the user.

    The raw declaration stores exactly what the user has written (i.e. the AST), without
    any additional checking or parsing.
    """

    python_func: PyFunc
    description: str = field(default="function", init=False)

    def parse(self, globals: Globals) -> "CheckedFunctionDecl":
        """Parses and checks the user-provided signature of the function."""
        func_ast = parse_py_func(self.python_func)
        ty = check_signature(func_ast, globals)
        if not has_empty_body(func_ast):
            raise GuppyError(
                "Body of function declaration must be empty", func_ast.body[0]
            )
        return CheckedFunctionDecl(self.id, self.name, func_ast, ty, self.python_func)


@dataclass(frozen=True)
class CheckedFunctionDecl(RawFunctionDecl, CompilableDef, CallableDef):
    """A function declaration with parsed and checked signature.

    In particular, this means that we have determined a type for the function.
    """

    defined_at: ast.FunctionDef

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
    ) -> tuple[GlobalCall, Type]:
        """Synthesizes the return type of a function call."""
        # Use default implementation from the expression checker
        args, ty, inst = synthesize_call(self.ty, args, node, ctx)
        node = with_loc(node, GlobalCall(def_id=self.id, args=args, type_args=inst))
        return node, ty

    def compile_outer(self, graph: Hugr, parent: Node) -> "CompiledFunctionDecl":
        """Adds a Hugr `FuncDecl` node for this funciton to the Hugr."""
        node = graph.add_declare(self.ty, parent, self.name)
        return CompiledFunctionDecl(
            self.id, self.name, self.defined_at, self.ty, self.python_func, node
        )


@dataclass(frozen=True)
class CompiledFunctionDecl(CheckedFunctionDecl, CompiledCallableDef):
    """A function declaration with a corresponding Hugr node."""

    hugr_node: VNode

    def load(
        self, dfg: DFContainer, graph: Hugr, globals: CompiledGlobals, node: AstNode
    ) -> OutPortV:
        """Loads the function as a value into a local Hugr dataflow graph."""
        assert self.hugr_node is not None
        return graph.add_load_constant(self.hugr_node.out_port(0), dfg.node).out_port(0)

    def compile_call(
        self,
        args: list[OutPortV],
        type_args: Inst,
        dfg: DFContainer,
        graph: Hugr,
        globals: CompiledGlobals,
        node: AstNode,
    ) -> list[OutPortV]:
        """Compiles a call to the function."""
        assert self.hugr_node is not None
        # TODO: Hugr should probably allow us to pass type args to `Call`, so we can
        #   avoid loading the function to manually add a `TypeApply`
        if type_args:
            func = self.load(dfg, graph, globals, node)
            func = graph.add_type_apply(func, type_args, dfg.node)
            call = graph.add_indirect_call(func.out_port(0), args, dfg.node)
        else:
            call = graph.add_call(self.hugr_node.out_port(0), args, dfg.node)
        return [call.out_port(i) for i in range(len(type_to_row(self.ty.output)))]
