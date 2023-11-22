import ast
from dataclasses import dataclass
from typing import Optional

from guppy.ast_util import AstNode, has_empty_body
from guppy.checker.core import Globals, Context
from guppy.checker.func_checker import check_signature
from guppy.compiler.core import CompiledFunction, DFContainer, CompiledGlobals
from guppy.error import GuppyError
from guppy.gtypes import type_to_row, GuppyType
from guppy.hugr.hugr import VNode, Hugr, Node, OutPortV
from guppy.nodes import GlobalCall


@dataclass
class DeclaredFunction(CompiledFunction):
    """A user-declared function that compiles to a Hugr function declaration."""

    node: Optional[VNode] = None

    @staticmethod
    def from_ast(
        func_def: ast.FunctionDef, name: str, globals: Globals
    ) -> "DeclaredFunction":
        ty = check_signature(func_def, globals)
        if not has_empty_body(func_def):
            raise GuppyError(
                "Body of function declaration must be empty", func_def.body[0]
            )
        return DeclaredFunction(name, ty, func_def, None)

    def check_call(
        self, args: list[ast.expr], ty: GuppyType, node: AstNode, ctx: Context
    ) -> GlobalCall:
        raise NotImplementedError

    def synthesize_call(
        self, args: list[ast.expr], node: AstNode, ctx: Context
    ) -> tuple[GlobalCall, GuppyType]:
        raise NotImplementedError

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
        dfg: DFContainer,
        graph: Hugr,
        globals: CompiledGlobals,
        node: AstNode,
    ) -> list[OutPortV]:
        assert self.node is not None
        call = graph.add_call(self.node.out_port(0), args, dfg.node)
        return [call.out_port(i) for i in range(len(type_to_row(self.ty.returns)))]
