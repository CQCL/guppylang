import ast
from collections.abc import Sequence

from hugr import Wire, ops
from hugr.build.dfg import DfBase

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
from guppylang.nodes import CheckedNestedFunctionDef, PlaceNode
from guppylang.tys.ty import TupleType, Type


class StmtCompiler(CompilerBase, AstVisitor[None]):
    """A compiler for Guppy statements to Hugr"""

    expr_compiler: ExprCompiler

    dfg: DFContainer

    def __init__(self, globals: CompiledGlobals):
        super().__init__(globals)
        self.expr_compiler = ExprCompiler(globals)

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

    @property
    def builder(self) -> DfBase[ops.DfParentOp]:
        """The Hugr dataflow graph builder."""
        return self.dfg.builder

    def _unpack_assign(self, lhs: ast.expr, port: Wire, node: ast.stmt) -> None:
        """Updates the local DFG with assignments."""
        if isinstance(lhs, PlaceNode):
            self.dfg[lhs.place] = port
        elif isinstance(lhs, ast.Tuple):
            types = [get_type(e).to_hugr() for e in lhs.elts]
            unpack = self.builder.add_op(ops.UnpackTuple(types), port)
            for pat, wire in zip(lhs.elts, unpack, strict=True):
                self._unpack_assign(pat, wire, node)
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

            row: list[tuple[Wire, Type]]
            if isinstance(return_ty, TupleType):
                types = [e.to_hugr() for e in return_ty.element_types]
                unpack = self.builder.add_op(ops.UnpackTuple(types), port)
                row = list(zip(unpack, return_ty.element_types, strict=True))
            else:
                row = [(port, return_ty)]

            for i, (wire, ty) in enumerate(row):
                var = Variable(return_var(i), ty, node.value)
                self.dfg[var] = wire

    def visit_CheckedNestedFunctionDef(self, node: CheckedNestedFunctionDef) -> None:
        from guppylang.compiler.func_compiler import compile_local_func_def

        var = Variable(node.name, node.ty, node)
        loaded_func = compile_local_func_def(node, self.dfg, self.globals)
        self.dfg[var] = loaded_func
