import ast
import collections
import itertools
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional, NamedTuple, Iterator, Union

from guppy.analysis import (
    LivenessDomain,
    LivenessAnalysis,
    AssignmentAnalysis,
    DefAssignmentDomain,
    MaybeAssignmentDomain,
    Result,
)
from guppy.bb import BB, VarRow, Signature, CompiledBB
from guppy.compiler_base import VarMap, DFContainer, Variable
from guppy.error import InternalGuppyError, GuppyError, assert_bool_type
from guppy.ast_util import AstVisitor, line_col, set_location_from
from guppy.expression import ExpressionCompiler
from guppy.guppy_types import GuppyType, TupleType, SumType
from guppy.hugr.hugr import Node, Hugr, OutPortV
from guppy.statement import StatementCompiler


class CFG:
    """A control-flow graph of basic blocks."""

    bbs: list[BB]
    entry_bb: BB
    exit_bb: BB

    live_before: Result[LivenessDomain]
    ass_before: Result[DefAssignmentDomain]
    maybe_ass_before: Result[MaybeAssignmentDomain]

    def __init__(self) -> None:
        self.bbs = []
        self.entry_bb = self.new_bb()
        self.exit_bb = self.new_bb()
        self.live_before = {}
        self.ass_before = {}
        self.maybe_ass_before = {}

    def new_bb(self, *preds: BB, statements: Optional[list[ast.stmt]] = None) -> BB:
        """Adds a new basic block to the CFG."""
        bb = BB(len(self.bbs), predecessors=list(preds), statements=statements or [])
        self.bbs.append(bb)
        for p in preds:
            p.successors.append(bb)
        return bb

    def link(self, src_bb: BB, tgt_bb: BB) -> None:
        """Adds a control-flow edge between two basic blocks."""
        src_bb.successors.append(tgt_bb)
        tgt_bb.predecessors.append(src_bb)

    def compile(
        self,
        graph: Hugr,
        input_row: VarRow,
        return_tys: list[GuppyType],
        parent: Node,
        global_variables: VarMap,
    ) -> None:
        """Compiles the CFG."""

        # First, we need to run program analysis
        for bb in self.bbs:
            bb.compute_variable_stats(len(return_tys))
        self.live_before = LivenessAnalysis().run(self.bbs)
        self.ass_before, self.maybe_ass_before = AssignmentAnalysis(
            self.bbs, {v.name for v in input_row}
        ).run_unpacked(self.bbs)

        # We start by compiling the entry BB
        entry_compiled = self._compile_bb(
            self.entry_bb, input_row, return_tys, graph, parent, global_variables
        )
        compiled = {self.entry_bb: entry_compiled}

        # Visit all control-flow edges in BFS order. We can't just do a normal loop over
        # all BBs since the input types for a BB are computed by compiling a predecessor
        queue = collections.deque(
            (entry_compiled, i, succ) for i, succ in enumerate(self.entry_bb.successors)
        )
        while len(queue) > 0:
            pred, num_output, bb = queue.popleft()
            out_row = pred.sig.output_rows[num_output]

            if bb in compiled:
                # If the BB was already compiled, we just have to check that the
                # signatures match.
                self._check_rows_match(out_row, compiled[bb].sig.input_row, bb)
            else:
                # Otherwise, compile the BB and enqueue its successors
                compiled_bb = self._compile_bb(
                    bb, out_row, return_tys, graph, parent, global_variables
                )
                queue += [
                    (compiled_bb, i, succ) for i, succ in enumerate(bb.successors)
                ]
                compiled[bb] = compiled_bb

            graph.add_edge(
                pred.node.out_port(num_output), compiled[bb].node.in_port(None)
            )

    def _compile_bb(
        self,
        bb: BB,
        input_row: VarRow,
        return_tys: list[GuppyType],
        graph: Hugr,
        parent: Node,
        global_variables: VarMap,
    ) -> CompiledBB:
        """Compiles a single basic block."""

        # The exit BB is completely empty
        if len(bb.successors) == 0:
            block = graph.add_exit(return_tys, parent)
            return CompiledBB(block, bb, Signature(input_row, []))

        # For the entry BB we have to separately check that all used variables are
        # defined. For all other BBs, this will be checked when compiling a predecessor.
        if len(bb.predecessors) == 0:
            for x, use in bb.vars.used.items():
                if x not in self.ass_before[bb] and x not in global_variables:
                    raise GuppyError(f"Variable `{x}` is not defined", use)

        # Compile the basic block
        block = graph.add_block(parent, num_successors=len(bb.successors))
        inp = graph.add_input(output_tys=[v.ty for v in input_row], parent=block)
        dfg = DFContainer(
            block,
            {
                v.name: Variable(v.name, inp.out_port(i), v.defined_at)
                for (i, v) in enumerate(input_row)
            },
        )
        stmt_compiler = StatementCompiler(graph, global_variables)
        dfg = stmt_compiler.compile_stmts(bb.statements, dfg, return_tys)

        for succ in bb.successors:
            for x, use_bb in self.live_before[succ].items():
                # Check that the variable requested by the successor are defined
                if x not in dfg and x not in global_variables:
                    # If the variable is defined on *some* paths, we can give a more
                    # informative error message
                    if x in self.maybe_ass_before[use_bb]:
                        # TODO: This should be "Variable x is not defined when coming
                        #  from {bb}". But for this we need a way to associate BBs with
                        #  source locations.
                        raise GuppyError(
                            f"Variable `{x}` is not defined on all control-flow paths.",
                            use_bb.vars.used[x],
                        )
                    raise GuppyError(
                        f"Variable `{x}` is not defined", use_bb.vars.used[x]
                    )

                # We have to check that used linear variables are not being outputted
                if x in dfg:
                    var = dfg[x]
                    if var.ty.linear and var.used:
                        raise GuppyError(
                            f"Variable `{x}` with linear type `{var.ty}` was "
                            "already used (at {0})",
                            self.live_before[succ][x].vars.used[x],
                            [var.used],
                        )

            # On the other hand, unused linear variables *must* be outputted
            for x, var in dfg.variables.items():
                if var.ty.linear and not var.used and x not in self.live_before[succ]:
                    # TODO: This should be "Variable x with linear type ty is not
                    #  used in {bb}". But for this we need a way to associate BBs with
                    #  source locations.
                    raise GuppyError(
                        f"Variable `{x}` with linear type `{var.ty}` is "
                        "not used on all control-flow paths",
                        var.defined_at,
                    )

        # Finally, we have to add the block output. The easy case is if we don't branch:
        # We just output the variables that are live in the successor
        output_vars = sorted(
            dfg[x] for x in self.live_before[bb.successors[0]] if x in dfg
        )
        if len(bb.successors) == 1:
            # Even if we don't branch, we still have to add a `Sum(())` predicate
            unit = graph.add_make_tuple([], parent=block).out_port(0)
            branch_port = graph.add_tag(
                variants=[TupleType([])], tag=0, inp=unit, parent=block
            ).out_port(0)
        else:
            # If we branch, we have to compile the branch predicate
            assert bb.branch_pred is not None
            expr_compiler = ExpressionCompiler(graph, global_variables)
            branch_port = expr_compiler.compile(bb.branch_pred, dfg)
            assert_bool_type(branch_port.ty, bb.branch_pred)
            first, *rest = bb.successors
            # If the branches use different variables, we have to output a Sum-type
            # predicate
            if any(
                self.live_before[r].keys() != self.live_before[first].keys()
                for r in rest
            ):
                # We put all non-linear variables into the branch predicate and all
                # linear variables in the normal output (since they are shared between
                # all successors). This is in line with the definition of `<` on
                # variables which puts linear variables at the end.
                branch_port = self._choose_vars_for_pred(
                    graph=graph,
                    pred=branch_port,
                    output_vars=[
                        sorted(
                            x
                            for x in self.live_before[succ]
                            if x in dfg and not dfg[x].ty.linear
                        )
                        for succ in bb.successors
                    ],
                    dfg=dfg,
                )
                output_vars = sorted(
                    dfg[x]
                    # We can look at `successors[0]` here since all successors must have
                    # the same `live_before` linear variables
                    for x in self.live_before[bb.successors[0]]
                    if x in dfg and dfg[x].ty.linear
                )

        graph.add_output(
            inputs=[branch_port] + [v.port for v in output_vars], parent=block
        )
        output_rows = [
            sorted([dfg[x] for x in self.live_before[succ] if x in dfg])
            for succ in bb.successors
        ]

        return CompiledBB(block, bb, Signature(input_row, output_rows))

    def _check_rows_match(self, row1: VarRow, row2: VarRow, bb: BB) -> None:
        """Checks that the types of two rows match up.

        Otherwise, an error is thrown, alerting the user that a variable has different
        types on different control-flow paths.
        """
        assert len(row1) == len(row2)
        for v1, v2 in zip(row1, row2):
            assert v1.name == v2.name
            if v1.ty != v2.ty:
                # In the error message, we want to mention the variable that was first
                # defined at the start.
                if line_col(v2.defined_at) < line_col(v1.defined_at):
                    v1, v2 = v2, v1
                # We shouldn't mention temporary variables (starting with `%`)
                # in error messages:
                ident = (
                    "Expression" if v1.name.startswith("%") else f"Variable `{v1.name}`"
                )
                raise GuppyError(
                    f"{ident} can refer to different types: "
                    f"`{v1.ty}` (at {{}}) vs `{v2.ty}` (at {{}})",
                    self.live_before[bb][v1.name].vars.used[v1.name],
                    [v1.defined_at, v2.defined_at],
                )

    @staticmethod
    def _choose_vars_for_pred(
        graph: Hugr, pred: OutPortV, output_vars: list[list[str]], dfg: DFContainer
    ) -> OutPortV:
        """Selects an output based on a predicate.

        Given `pred: Sum((), (), ...)` and output variable sets `#s1, #s2, ...`,
        constructs a predicate value of type `Sum(Tuple(#s1), Tuple(#s2), ...)`.
        """
        assert isinstance(pred.ty, SumType)
        assert len(pred.ty.element_types) == len(output_vars)
        tuples = [
            graph.add_make_tuple(
                inputs=[dfg[x].port for x in sorted(vs) if x in dfg], parent=dfg.node
            ).out_port(0)
            for vs in output_vars
        ]
        tys = [t.ty for t in tuples]
        conditional = graph.add_conditional(
            cond_input=pred, inputs=tuples, parent=dfg.node
        )
        for i, ty in enumerate(tys):
            case = graph.add_case(conditional)
            inp = graph.add_input(output_tys=tys, parent=case).out_port(i)
            tag = graph.add_tag(variants=tys, tag=i, inp=inp, parent=case).out_port(0)
            graph.add_output(inputs=[tag], parent=case)
        return conditional.add_out_port(SumType(tys))


class Jumps(NamedTuple):
    """Holds jump targets for return, continue, and break during CFG construction."""

    return_bb: BB
    continue_bb: Optional[BB]
    break_bb: Optional[BB]


class CFGBuilder(AstVisitor[Optional[BB]]):
    """Constructs a CFG from ast nodes."""

    cfg: CFG
    num_returns: int

    def build(self, nodes: list[ast.stmt], num_returns: int) -> CFG:
        """Builds a CFG from a list of ast nodes.

        We also require the expected number of return ports for the whole CFG. This is
        needed to translate return statements into assignments of dummy return
        variables.
        """
        self.cfg = CFG()
        self.num_returns = num_returns

        final_bb = self.visit_stmts(
            nodes, self.cfg.entry_bb, Jumps(self.cfg.exit_bb, None, None)
        )

        # If we're still in a basic block after compiling the whole body, we have to add
        # an implicit void return
        if final_bb is not None:
            if num_returns > 0:
                raise GuppyError("Expected return statement", nodes[-1])
            self.cfg.link(final_bb, self.cfg.exit_bb)

        return self.cfg

    def visit_stmts(self, nodes: list[ast.stmt], bb: BB, jumps: Jumps) -> Optional[BB]:
        bb_opt: Optional[BB] = bb
        next_functional = False
        for node in nodes:
            if bb_opt is None:
                raise GuppyError("Unreachable code", node)
            if is_functional_annotation(node):
                next_functional = True
                continue

            if next_functional:
                # TODO: This should be an assertion that the Hugr can be un-flattened
                raise NotImplementedError()
                next_functional = False
            else:
                bb_opt = self.visit(node, bb_opt, jumps)
        return bb_opt

    def _build_node_value(
        self, node: Union[ast.Assign, ast.AugAssign, ast.Return], bb: BB
    ) -> BB:
        """Utility method for building a node containing a `value` expression.

        Builds the expression and mutates `node.value` to point to the built expression.
        Returns the BB in which the expression is available and adds the node to it.
        """
        if node.value is not None:
            node.value, bb = ExprBuilder.build(node.value, self.cfg, bb)
        bb.statements.append(node)
        return bb

    def visit_Assign(self, node: ast.Assign, bb: BB, jumps: Jumps) -> Optional[BB]:
        return self._build_node_value(node, bb)

    def visit_AugAssign(
        self, node: ast.AugAssign, bb: BB, jumps: Jumps
    ) -> Optional[BB]:
        return self._build_node_value(node, bb)

    def visit_Expr(self, node: ast.Expr, bb: BB, jumps: Jumps) -> Optional[BB]:
        # This is an expression statement where the value is discarded
        _, bb = ExprBuilder.build(node.value, self.cfg, bb)
        return bb

    def visit_If(self, node: ast.If, bb: BB, jumps: Jumps) -> Optional[BB]:
        then_bb, else_bb = self.cfg.new_bb(), self.cfg.new_bb()
        BranchBuilder.build(node.test, self.cfg, bb, then_bb, else_bb)
        then_bb = self.visit_stmts(node.body, then_bb, jumps)
        else_bb = self.visit_stmts(node.orelse, else_bb, jumps)
        # We need to handle different cases depending on whether branches jump (i.e.
        # return, continue, or break)
        if then_bb is None:
            # If branch jumps: We continue in the BB of the else branch
            return else_bb
        elif else_bb is None:
            # Else branch jumps: We continue in the BB of the if branch
            return then_bb
        else:
            # No branch jumps: We have to merge the control flow
            return self.cfg.new_bb(then_bb, else_bb)

    def visit_While(self, node: ast.While, bb: BB, jumps: Jumps) -> Optional[BB]:
        head_bb = self.cfg.new_bb(bb)
        body_bb, tail_bb = self.cfg.new_bb(), self.cfg.new_bb()
        BranchBuilder.build(node.test, self.cfg, head_bb, body_bb, tail_bb)

        new_jumps = Jumps(
            return_bb=jumps.return_bb, continue_bb=head_bb, break_bb=tail_bb
        )
        body_end_bb = self.visit_stmts(node.body, body_bb, new_jumps)

        # Go back to the head (but only the body doesn't do its jumping)
        if body_end_bb is not None:
            self.cfg.link(body_end_bb, head_bb)

        # Continue compilation in the tail. This should even happen if the body does
        # its own jumps since the body is not guaranteed to execute
        return tail_bb

    def visit_Continue(self, node: ast.Continue, bb: BB, jumps: Jumps) -> Optional[BB]:
        if not jumps.continue_bb:
            raise InternalGuppyError("Continue BB not defined")
        self.cfg.link(bb, jumps.continue_bb)
        return None

    def visit_Break(self, node: ast.Break, bb: BB, jumps: Jumps) -> Optional[BB]:
        if not jumps.break_bb:
            raise InternalGuppyError("Break BB not defined")
        self.cfg.link(bb, jumps.break_bb)
        return None

    def visit_Return(self, node: ast.Return, bb: BB, jumps: Jumps) -> Optional[BB]:
        bb = self._build_node_value(node, bb)
        self.cfg.link(bb, jumps.return_bb)
        return None

    def visit_Pass(self, node: ast.Pass, bb: BB, jumps: Jumps) -> Optional[BB]:
        return bb

    def generic_visit(self, node: ast.AST, bb: BB, jumps: Jumps) -> Optional[BB]:  # type: ignore
        # When adding support for new statements, we have to remember to use the
        # ExprBuilder to transform all included expressions!
        raise GuppyError("Statement is not supported", node)


# In order to build expressions, need an endless stream of unique temporary variables
# to store intermediate results
tmp_vars: Iterator[str] = (f"%tmp{i}" for i in itertools.count())


class ExprBuilder(ast.NodeTransformer):
    """Builds an expression into a basic block."""

    cfg: CFG
    bb: BB

    def __init__(self, cfg: CFG, start_bb: BB) -> None:
        self.cfg = cfg
        self.bb = start_bb

    @staticmethod
    def build(node: ast.expr, cfg: CFG, bb: BB) -> tuple[ast.expr, BB]:
        """Builds an expression into a CFG.

        The expression may be transformed and new basic blocks may be created (for
        example for `... if ... else ...` expressions). Returns the new expression and
        the final basic block in which the expression can be used."""
        builder = ExprBuilder(cfg, bb)
        return builder.visit(node), builder.bb

    @classmethod
    def _make_var(cls, name: str, loc: Optional[ast.expr] = None) -> ast.Name:
        """Creates an `ast.Name` node."""
        node = ast.Name(id=name, ctx=ast.Load)
        if loc is not None:
            set_location_from(node, loc)
        return node

    @classmethod
    def _tmp_assign(cls, tmp_name: str, value: ast.expr, bb: BB) -> None:
        """Adds a temporary variable assignment to a basic block."""
        node = ast.Assign(targets=[cls._make_var(tmp_name, value)], value=value)
        set_location_from(node, value)
        bb.statements.append(node)

    def visit_Name(self, node: ast.Name) -> ast.Name:
        return node

    def visit_NamedExpr(self, node: ast.NamedExpr) -> ast.Name:
        # This is an assignment expression, e.g. `x := 42`. We turn it into an
        # assignment statement and replace the expression with `x`.
        if not isinstance(node.target, ast.Name):
            raise InternalGuppyError(f"Unexpected assign target: {node.target}")
        assign = ast.Assign(targets=[node.target], value=self.visit(node.value))
        set_location_from(assign, node)
        self.bb.statements.append(assign)
        return node.target

    def visit_IfExp(self, node: ast.IfExp) -> ast.Name:
        if_bb, else_bb = self.cfg.new_bb(), self.cfg.new_bb()
        BranchBuilder.build(node.test, self.cfg, self.bb, if_bb, else_bb)

        if_expr, if_bb = self.build(node.body, self.cfg, if_bb)
        else_expr, else_bb = self.build(node.orelse, self.cfg, else_bb)

        # Assign the result to a temporary variable
        tmp = next(tmp_vars)
        self._tmp_assign(tmp, if_expr, if_bb)
        self._tmp_assign(tmp, else_expr, else_bb)

        # Merge the temporary variables in a new BB
        merge_bb = self.cfg.new_bb(if_bb, else_bb)
        self.bb = merge_bb

        # The final value is stored in the temporary variable
        return self._make_var(tmp, node)

    def generic_visit(self, node: ast.AST) -> ast.AST:
        # Short-circuit expressions must be built using the `BranchBuilder`. However, we
        # can turn them into regular expressions by assigning True/False to a temporary
        # variable and merging the control-flow
        if is_short_circuit_expr(node):
            assert isinstance(node, ast.expr)
            true_bb, false_bb = self.cfg.new_bb(), self.cfg.new_bb()
            BranchBuilder.build(node, self.cfg, self.bb, true_bb, false_bb)
            true_const = ast.Constant(value=True)
            false_const = ast.Constant(value=False)
            set_location_from(true_const, node)
            set_location_from(false_const, node)
            tmp = next(tmp_vars)
            self._tmp_assign(tmp, true_const, true_bb)
            self._tmp_assign(tmp, false_const, false_bb)
            merge_bb = self.cfg.new_bb(true_bb, false_bb)
            self.bb = merge_bb
            return self._make_var(tmp, node)
        # For all other expressions, just recurse deeper with the node transformer
        return super().generic_visit(node)


class BranchBuilder(AstVisitor[None]):
    """Builds an expression and does branching based on the value.

    This builder should be used to handle all branching on boolean values since it
    handles short-circuit evaluation etc.
    """

    cfg: CFG

    def __init__(self, cfg: CFG):
        """Creates a new `BranchBuilder`."""
        self.cfg = cfg

    @staticmethod
    def build(node: ast.expr, cfg: CFG, bb: BB, true_bb: BB, false_bb: BB) -> None:
        """Builds an expression and branches to `true_bb` or `false_bb`, depending on
        the truth value of the expression."""
        builder = BranchBuilder(cfg)
        builder.visit(node, bb, true_bb, false_bb)

    def visit_BoolOp(self, node: ast.BoolOp, bb: BB, true_bb: BB, false_bb: BB) -> None:
        # Add short-circuit evaluation of boolean expression. If there are more than 2
        # operators, we turn the flat operator list into a right-nested tree to allow
        # for recursive processing.
        assert len(node.values) > 1
        if len(node.values) > 2:
            r = ast.BoolOp(
                op=node.op,
                values=node.values[1:],
                lineno=node.values[0].lineno,
                col_offset=node.values[0].col_offset,
                end_lineno=node.values[-1].end_lineno,
                end_col_offset=node.values[-1].end_col_offset,
            )
            node.values = [node.values[0], r]
        [left, right] = node.values

        extra_bb = self.cfg.new_bb()
        assert type(node.op) in [ast.And, ast.Or]
        if isinstance(node.op, ast.And):
            self.visit(left, bb, extra_bb, false_bb)
        elif isinstance(node.op, ast.Or):
            self.visit(left, bb, true_bb, extra_bb)
        self.visit(right, extra_bb, true_bb, false_bb)

    def visit_UnaryOp(
        self, node: ast.UnaryOp, bb: BB, true_bb: BB, false_bb: BB
    ) -> None:
        # For `not` operator, we can just switch `true_bb` and `false_bb`
        if isinstance(node.op, ast.Not):
            self.visit(node.operand, bb, false_bb, true_bb)
        else:
            self.generic_visit(node, bb, true_bb, false_bb)

    def visit_Compare(
        self, node: ast.Compare, bb: BB, true_bb: BB, false_bb: BB
    ) -> None:
        # Support chained comparisons, e.g. `x <= 5 < y` by compiling to `x <= 5 and
        # 5 < y`. This way we get short-circuit evaluation for free.
        if len(node.comparators) > 1:
            comparators = [node.left] + node.comparators
            values = [
                ast.Compare(
                    left=left,
                    ops=[op],
                    comparators=[right],
                    lineno=left.lineno,
                    col_offset=left.col_offset,
                    end_lineno=right.end_lineno,
                    end_col_offset=right.end_col_offset,
                )
                for left, op, right in zip(comparators[:-1], node.ops, comparators[1:])
            ]
            conj = ast.BoolOp(op=ast.And(), values=values)
            set_location_from(conj, node)
            self.visit_BoolOp(conj, bb, true_bb, false_bb)
        else:
            self.generic_visit(node, bb, true_bb, false_bb)

    def visit_IfExp(self, node: ast.IfExp, bb: BB, true_bb: BB, false_bb: BB) -> None:
        then_bb, else_bb = self.cfg.new_bb(), self.cfg.new_bb()
        self.visit(node.test, bb, then_bb, else_bb)
        self.visit(node.body, then_bb, true_bb, false_bb)
        self.visit(node.orelse, else_bb, true_bb, false_bb)

    def generic_visit(self, node: ast.expr, bb: BB, true_bb: BB, false_bb: BB) -> None:  # type: ignore
        # We can always fall back to building the node as a regular expression and using
        # the result as a branch predicate
        pred, bb = ExprBuilder.build(node, self.cfg, bb)
        bb.branch_pred = pred
        self.cfg.link(bb, true_bb)
        self.cfg.link(bb, false_bb)


def is_functional_annotation(stmt: ast.stmt) -> bool:
    """Returns `True` iff the given statement is the functional pseudo-decorator.

    Pseudo-decorators are built using the matmul operator `@`, i.e. `_@functional`.
    """
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.BinOp):
        op = stmt.value
        if (
            isinstance(op.op, ast.MatMult)
            and isinstance(op.left, ast.Name)
            and isinstance(op.right, ast.Name)
        ):
            return op.left.id == "_" and op.right.id == "functional"
    return False


def is_short_circuit_expr(node: ast.AST) -> bool:
    """Checks if an expression uses short-circuiting.

    Those expressions *must* be compiled using the `BranchBuilder`.
    """
    return isinstance(node, ast.BoolOp) or (
        isinstance(node, ast.Compare) and len(node.comparators) > 1
    )
