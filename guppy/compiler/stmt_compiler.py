import ast
from typing import Sequence

from guppy.ast_util import AstVisitor
from guppy.checker.cfg_checker import CheckedBB
from guppy.compiler.core import (
    CompilerBase,
    DFContainer,
    CompiledGlobals,
    PortVariable,
    return_var,
)
from guppy.compiler.expr_compiler import ExprCompiler
from guppy.error import InternalGuppyError
from guppy.gtypes import TupleType
from guppy.hugr.hugr import Hugr, OutPortV
from guppy.nodes import CheckedNestedFunctionDef


class StmtCompiler(CompilerBase, AstVisitor[None]):
    """A compiler for Guppy statements to Hugr"""

    expr_compiler: ExprCompiler

    bb: CheckedBB
    dfg: DFContainer

    def __init__(self, graph: Hugr, globals: CompiledGlobals):
        super().__init__(graph, globals)
        self.expr_compiler = ExprCompiler(graph, globals)

    def compile_stmts(
        self,
        stmts: Sequence[ast.stmt],
        bb: CheckedBB,
        dfg: DFContainer,
    ) -> DFContainer:
        """Compiles a list of basic statements into a dataflow node.

        Note that the `dfg` is mutated in-place. After compilation, the DFG will also
        contain all variables that are assigned in the given list of statements.
        """
        self.bb = bb
        self.dfg = dfg
        for s in stmts:
            self.visit(s)
        return self.dfg

    def _unpack_assign(self, lhs: ast.expr, port: OutPortV, node: ast.stmt) -> None:
        """Updates the local DFG with assignments."""
        if isinstance(lhs, ast.Name):
            x = lhs.id
            self.dfg[x] = PortVariable(x, port, node)
        elif isinstance(lhs, ast.Tuple):
            unpack = self.graph.add_unpack_tuple(port, self.dfg.node)
            for i, pat in enumerate(lhs.elts):
                self._unpack_assign(pat, unpack.out_port(i), node)
        else:
            raise InternalGuppyError("Invalid assign pattern in compiler")

    def visit_Assign(self, node: ast.Assign) -> None:
        [target] = node.targets
        port = self.expr_compiler.compile(node.value, self.dfg)
        self._unpack_assign(target, port, node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        assert node.value is not None
        port = self.expr_compiler.compile(node.value, self.dfg)
        self._unpack_assign(node.target, port, node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        raise InternalGuppyError("Node should have been removed during type checking.")

    def visit_Expr(self, node: ast.Expr) -> None:
        self.expr_compiler.compile_row(node.value, self.dfg)

    def visit_Return(self, node: ast.Return) -> None:
        # We turn returns into assignments of dummy variables, i.e. the statement
        # `return e0, e1, e2` is turned into `%ret0 = e0; %ret1 = e1; %ret2 = e2`.
        if node.value is not None:
            port = self.expr_compiler.compile(node.value, self.dfg)
            if isinstance(port.ty, TupleType):
                unpack = self.graph.add_unpack_tuple(port, self.dfg.node)
                row = [unpack.out_port(i) for i in range(len(port.ty.element_types))]
            else:
                row = [port]
            for i, port in enumerate(row):
                name = return_var(i)
                self.dfg[name] = PortVariable(name, port, node)

    def visit_CheckedNestedFunctionDef(self, node: CheckedNestedFunctionDef) -> None:
        from guppy.compiler.func_compiler import compile_local_func_def

        self.dfg[node.name] = compile_local_func_def(
            node, self.dfg, self.graph, self.globals
        )
