import ast
from collections.abc import Sequence

from guppylang.ast_util import AstVisitor, get_type
from guppylang.checker.core import Variable
from guppylang.compiler.core import (
    CompiledGlobals,
    CompilerBase,
    DFContainer,
    return_var,
)
from guppylang.compiler.expr_compiler import ExprCompiler
from guppylang.error import InternalGuppyError
from guppylang.hugr_builder.hugr import Hugr, OutPortV
from guppylang.nodes import CheckedNestedFunctionDef, PlaceNode
from guppylang.tys.ty import TupleType


class StmtCompiler(CompilerBase, AstVisitor[None]):
    """A compiler for Guppy statements to Hugr"""

    expr_compiler: ExprCompiler

    dfg: DFContainer

    def __init__(self, graph: Hugr, globals: CompiledGlobals):
        super().__init__(graph, globals)
        self.expr_compiler = ExprCompiler(graph, globals)

    def compile_stmts(
        self,
        stmts: Sequence[ast.stmt],
        dfg: DFContainer,
    ) -> DFContainer:
        """Compiles a list of basic statements into a dataflow node.

        Note that the `dfg` is mutated in-place. After compilation, the DFG will also
        contain all variables that are assigned in the given list of statements.
        """
        self.dfg = dfg
        for s in stmts:
            self.visit(s)
        return self.dfg

    def _unpack_assign(self, lhs: ast.expr, port: OutPortV, node: ast.stmt) -> None:
        """Updates the local DFG with assignments."""
        if isinstance(lhs, PlaceNode):
            self.dfg[lhs.place] = port
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
            return_ty = get_type(node.value)
            port = self.expr_compiler.compile(node.value, self.dfg)
            if isinstance(return_ty, TupleType):
                unpack = self.graph.add_unpack_tuple(port, self.dfg.node)
                row = [unpack.out_port(i) for i in range(len(return_ty.element_types))]
            else:
                row = [port]
            for i, port in enumerate(row):
                var = Variable(return_var(i), port.ty, node.value)
                self.dfg[var] = port

    def visit_CheckedNestedFunctionDef(self, node: CheckedNestedFunctionDef) -> None:
        from guppylang.compiler.func_compiler import compile_local_func_def

        var = Variable(node.name, node.ty, node)
        self.dfg[var] = compile_local_func_def(node, self.dfg, self.graph, self.globals)
