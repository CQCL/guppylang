import ast
from typing import Sequence

from guppy.ast_util import AstVisitor, AstNode
from guppy.cfg.bb import BB, NestedFunctionDef
from guppy.compiler_base import (
    CompilerBase,
    DFContainer,
    Variable,
    return_var,
    VarMap,
)
from guppy.error import GuppyError, GuppyTypeError, InternalGuppyError
from guppy.expression import ExpressionCompiler
from guppy.guppy_types import TupleType, TypeRow, GuppyType
from guppy.hugr.hugr import OutPortV, Hugr


class StatementCompiler(CompilerBase, AstVisitor[None]):
    """A compiler for non-control-flow statements occurring in a basic block.

    Control-flow statements like loops or if-statements are not handled by this
    compiler. They should be turned into a CFG made up of multiple simple basic blocks.
    """

    expr_compiler: ExpressionCompiler

    bb: BB
    dfg: DFContainer
    return_tys: list[GuppyType]

    def __init__(self, graph: Hugr, global_variables: VarMap):
        super().__init__(graph, global_variables)
        self.expr_compiler = ExpressionCompiler(graph, global_variables)

    def compile_stmts(
        self,
        stmts: Sequence[ast.stmt],
        bb: BB,
        dfg: DFContainer,
        return_tys: list[GuppyType],
    ) -> DFContainer:
        """Compiles a list of basic statements into a dataflow node.

        Note that the `dfg` is mutated in-place. After compilation, the DFG will also
        contain all variables that are assigned in the given list of statements.
        """
        self.bb = bb
        self.dfg = dfg
        self.return_tys = return_tys
        for s in stmts:
            self.visit(s)
        return self.dfg

    def visit_Assign(self, node: ast.Assign) -> None:
        if len(node.targets) > 1:
            # This is the case for assignments like `a = b = 1`
            raise GuppyError("Multi assignment not supported", node)
        target = node.targets[0]
        row = self.expr_compiler.compile_row(node.value, self.dfg)
        if len(row) == 0:
            # In Python it's fine to assign a void return with the variable being bound
            # to `None` afterward. At the moment, we don't have a `None` type in Guppy,
            # so we raise an error for now.
            # TODO: Think about this. Maybe we should uniformly treat `None` as the
            #  empty tuple?
            raise GuppyError("Cannot unpack empty row")
        assert len(row) > 0

        # Helper function to unpack the row based on the LHS pattern
        def unpack(pattern: AstNode, ports: list[OutPortV]) -> None:
            # Easiest case is if the LHS pattern is a single variable. Note we
            # implicitly pack the row into a tuple if it has more than one element.
            # I.e. `x = 1, 2` works just like `x = (1, 2)`.
            if isinstance(pattern, ast.Name):
                port = (
                    ports[0]
                    if len(ports) == 1
                    else self.graph.add_make_tuple(
                        inputs=ports, parent=self.dfg.node
                    ).out_port(0)
                )
                # Check if we override an unused linear variable
                x = pattern.id
                if x in self.dfg:
                    var = self.dfg[x]
                    if var.ty.linear and var.used is None:
                        raise GuppyError(
                            f"Variable `{x}` with linear type `{var.ty}` "
                            "is not used",
                            var.defined_at,
                        )
                self.dfg[x] = Variable(x, port, node)
            # The only other thing we support right now are tuples
            elif isinstance(pattern, ast.Tuple):
                if len(ports) == 1 and isinstance(ports[0].ty, TupleType):
                    ports = list(
                        self.graph.add_unpack_tuple(
                            input_tuple=ports[0], parent=self.dfg.node
                        ).out_ports
                    )
                n, m = len(pattern.elts), len(ports)
                if n != m:
                    raise GuppyTypeError(
                        f"{'Too many' if n < m else 'Not enough'} "
                        f"values to unpack (expected {n}, got {m})",
                        node,
                    )
                for pat, port in zip(pattern.elts, ports):
                    unpack(pat, [port])
            # TODO: Python also supports assignments like `[a, b] = [1, 2]` or
            #  `a, *b = ...`. The former would require some runtime checks but
            #  the latter should be easier to do (unpack and repack the rest).
            else:
                raise GuppyError("Assignment pattern not supported", pattern)

        unpack(target, row)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        # TODO: Figure out what to do with type annotations
        raise NotImplementedError()

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        # TODO: Set all source location attributes
        bin_op = ast.BinOp(left=node.target, op=node.op, right=node.value)
        assign = ast.Assign(
            targets=[node.target],
            value=bin_op,
            lineno=node.lineno,
            col_offset=node.col_offset,
        )
        self.visit_Assign(assign)

    def visit_Return(self, node: ast.Return) -> None:
        if node.value is None:
            row = []
        else:
            port = self.expr_compiler.compile(node.value, self.dfg)
            # Top-level tuples are unpacked, i.e. turned into a row
            if isinstance(port.ty, TupleType):
                unpack = self.graph.add_unpack_tuple(port, self.dfg.node)
                row = [unpack.out_port(i) for i in range(len(port.ty.element_types))]
            else:
                row = [port]

        tys = [p.ty for p in row]
        if tys != self.return_tys:
            raise GuppyTypeError(
                f"Return type mismatch: expected `{TypeRow(self.return_tys)}`, "
                f"got `{TypeRow(tys)}`",
                node.value,
            )

        # We turn returns into assignments of dummy variables, i.e. the statement
        # `return e0, e1, e2` is turned into `%ret0 = e0; %ret1 = e1; %ret2 = e2`.
        for i, port in enumerate(row):
            name = return_var(i)
            self.dfg[name] = Variable(name, port, node)

    def visit_NestedFunctionDef(self, node: NestedFunctionDef) -> None:
        from guppy.function import FunctionCompiler

        port = FunctionCompiler(self.graph, self.global_variables).compile_local(
            node, self.dfg, self.bb, self.global_variables
        )
        self.dfg[node.name] = Variable(node.name, port, node)

    def visit_If(self, node: ast.If) -> None:
        raise InternalGuppyError("Control-flow statement should not be present here.")

    def visit_While(self, node: ast.While) -> None:
        raise InternalGuppyError("Control-flow statement should not be present here.")

    def visit_Break(self, node: ast.Break) -> None:
        raise InternalGuppyError("Control-flow statement should not be present here.")

    def visit_Continue(self, node: ast.Continue) -> None:
        raise InternalGuppyError("Control-flow statement should not be present here.")
