import ast
from dataclasses import dataclass
from typing import TYPE_CHECKING

from guppylang.ast_util import AstNode, has_empty_body, with_loc
from guppylang.checker.core import Context, Globals
from guppylang.checker.expr_checker import check_call, synthesize_call
from guppylang.checker.func_checker import check_signature
from guppylang.compiler.core import CompiledFunction, CompiledGlobals, DFContainer
from guppylang.error import GuppyError
from guppylang.gtypes import GuppyType, Inst, Subst, type_to_row
from guppylang.hugr.hugr import Hugr, Node, OutPortV, VNode
from guppylang.nodes import GlobalCall

if TYPE_CHECKING:
    from guppylang.module import GuppyModule


@dataclass
class DeclaredFunction(CompiledFunction):
    """A user-declared function that compiles to a Hugr function declaration."""

    node: VNode | None = None

    @staticmethod
    def from_ast(
        func_def: ast.FunctionDef, name: str, module: "GuppyModule", globals: Globals
    ) -> "DeclaredFunction":
        ty = check_signature(func_def, globals)
        if not has_empty_body(func_def):
            raise GuppyError(
                "Body of function declaration must be empty", func_def.body[0]
            )
        return DeclaredFunction(name, ty, func_def, None, module)

    def check_call(
        self, args: list[ast.expr], ty: GuppyType, node: AstNode, ctx: Context
    ) -> tuple[ast.expr, Subst]:
        # Use default implementation from the expression checker
        args, subst, inst = check_call(self.ty, args, ty, node, ctx)
        return with_loc(node, GlobalCall(func=self, args=args, type_args=inst)), subst

    def synthesize_call(
        self, args: list[ast.expr], node: AstNode, ctx: Context
    ) -> tuple[GlobalCall, GuppyType]:
        # Use default implementation from the expression checker
        args, ty, inst = synthesize_call(self.ty, args, node, ctx)
        return with_loc(node, GlobalCall(func=self, args=args, type_args=inst)), ty

    def add_to_graph(self, graph: Hugr, parent: Node) -> None:
        self.node = graph.add_declare(self.ty, parent, self.name)

    def load(
        self, dfg: DFContainer, graph: Hugr, globals: CompiledGlobals, node: AstNode
    ) -> OutPortV:
        assert self.node is not None
        return graph.add_load_constant(self.node.out_port(0), dfg.node).out_port(0)

    def compile_call(
        self,
        args: list[OutPortV],
        type_args: Inst,
        dfg: DFContainer,
        graph: Hugr,
        globals: CompiledGlobals,
        node: AstNode,
    ) -> list[OutPortV]:
        assert self.node is not None
        # TODO: Hugr should probably allow us to pass type args to `Call`, so we can
        #   avoid loading the function to manually add a `TypeApply`
        if type_args:
            func = graph.add_load_constant(self.node.out_port(0), dfg.node)
            func = graph.add_type_apply(func.out_port(0), type_args, dfg.node)
            call = graph.add_indirect_call(func.out_port(0), args, dfg.node)
        else:
            call = graph.add_call(self.node.out_port(0), args, dfg.node)
        return [call.out_port(i) for i in range(len(type_to_row(self.ty.returns)))]
