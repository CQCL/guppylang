import ast
import collections
from dataclasses import dataclass, field
from typing import Optional, NamedTuple

from guppy.analysis import (
    LivenessDomain,
    LivenessAnalysis,
    AssignmentAnalysis,
    DefAssignmentDomain,
    MaybeAssignmentDomain,
    Result,
)
from guppy.bb import BB, VarRow, Signature
from guppy.compiler_base import VarMap, DFContainer, Variable
from guppy.error import InternalGuppyError, GuppyError, assert_bool_type
from guppy.ast_util import AstVisitor, line_col
from guppy.expression import ExpressionCompiler
from guppy.guppy_types import GuppyType, TupleType, SumType
from guppy.hugr.hugr import Node, Hugr, CFNode, OutPortV
from guppy.statement import StatementCompiler


@dataclass
class CompiledBB:
    """The result of compiling a basic block.

    Besides the corresponding node in the graph, we also store the signature of the
    basic block with type information.
    """

    node: CFNode
    bb: BB
    sig: Signature


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

    def new_bb(self, *preds: BB) -> BB:
        """Adds a new basic block to the CFG."""
        bb = BB(len(self.bbs), predecessors=list(preds))
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
            self.bbs
        ).run_unpacked(self.bbs)

        # Additionally, we can mark function arguments as definitely assigned
        args = {v.name for v in input_row}
        for bb in self.bbs:
            self.ass_before[bb] |= args

        # We start by compiling the entry BB
        entry_compiled = self._compile_bb(
            self.entry_bb, input_row, return_tys, graph, parent, global_variables
        )
        compiled = {self.entry_bb: entry_compiled}

        # Visit all control-flow edges in BFS order
        queue = collections.deque(
            (entry_compiled, i, succ) for i, succ in enumerate(self.entry_bb.successors)
        )
        while len(queue) > 0:
            pred, num_output, bb = queue.popleft()
            out_row = pred.sig.output_rows[num_output]

            if bb in compiled:
                # If the BB was already compiled, we just have to check that the
                # signatures match.
                self._assert_rows_match(out_row, compiled[bb].sig.input_row, bb)
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
        for x, use_bb in self.live_before[bb].items():
            if x in self.ass_before[bb] or x in global_variables:
                continue

            # The rest results in an error. If the variable is defined on *some*
            # paths, we can give a more informative error message
            if x in self.maybe_ass_before[use_bb]:
                # TODO: Can we point to the actual path in the message in a nice
                #  way?
                raise GuppyError(
                    f"Variable `{x}` is not defined on all control-flow paths.",
                    use_bb.vars.used[x],
                )
            else:
                raise GuppyError(f"Variable `{x}` is not defined", use_bb.vars.used[x])

        # The exit BB is completely empty
        if len(bb.successors) == 0:
            block = graph.add_exit(return_tys, parent)
            return CompiledBB(block, bb, Signature(input_row, []))

        block = graph.add_block(parent, num_sucessors=len(bb.successors))
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

        # The easy case is if we don't branch. We just output the variables that are
        # live in the successor
        output_vars = sorted(
            dfg[x] for x in self.live_before[bb.successors[0]] if x in dfg
        )
        if len(bb.successors) == 1:
            # Even if wo don't branch, we still have to add a unit `Sum(())` predicate
            unit = graph.add_make_tuple([], parent=block).out_port(0)
            branch_port = graph.add_tag(
                variants=[TupleType([])], tag=0, inp=unit, parent=block
            ).out_port(0)

        # If we branch, we have to compile the branch predicate
        else:
            assert bb.branch_pred is not None
            expr_compiler = ExpressionCompiler(graph, global_variables)
            branch_port = expr_compiler.compile(bb.branch_pred, dfg)
            assert_bool_type(branch_port.ty, bb.branch_pred)
            # If the branches use different variables, we have to use the predicate
            # output feature.
            if any(
                self.live_before[s].keys() != self.live_before[bb.successors[0]].keys()
                for s in bb.successors[1:]
            ):
                branch_port = self._make_predicate_output(
                    graph=graph,
                    pred=branch_port,
                    output_vars=[
                        sorted(self.live_before[succ].keys() & dfg.variables.keys())
                        for succ in bb.successors
                    ],
                    dfg=dfg,
                )
                output_vars = []

        graph.add_output(
            inputs=[branch_port] + [v.port for v in output_vars], parent=block
        )
        output_rows = [
            sorted([dfg[x] for x in self.live_before[succ] if x in dfg])
            for succ in bb.successors
        ]

        return CompiledBB(block, bb, Signature(input_row, output_rows))

    def _assert_rows_match(self, row1: VarRow, row2: VarRow, bb: BB) -> None:
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
                raise GuppyError(
                    f"Variable `{v1.name}` can refer to different types: "
                    f"`{v1.ty}` (at {{}}) vs `{v2.ty}` (at {{}})",
                    self.live_before[bb][v1.name].vars.used[v1.name],
                    [v1.defined_at, v2.defined_at],
                )

    @staticmethod
    def _make_predicate_output(
        graph: Hugr, pred: OutPortV, output_vars: list[list[str]], dfg: DFContainer
    ) -> OutPortV:
        """Selects an output based on a predicate.

        Given `pred: Sum((), (), ...)` and output variable sets `#s1, #s2, ...`,
        constructs a predicate value of type `Sum(Tuple(#s1), Tuple(#s2), ...)`.
        """
        assert isinstance(pred.ty, SumType) and len(pred.ty.element_types) == len(
            output_vars
        )
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
        return conditional.add_out_port(SumType([t.ty for t in tuples]))


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

    def visit_If(self, node: ast.If, bb: BB, jumps: Jumps) -> Optional[BB]:
        bb.branch_pred = node.test
        if_bb = self.visit_stmts(node.body, self.cfg.new_bb(bb), jumps)
        else_bb = self.visit_stmts(node.orelse, self.cfg.new_bb(bb), jumps)
        # We need to handle different cases depending on whether branches jump (i.e.
        # return, continue, or break)
        if if_bb is None:
            # If branch jumps: We continue in the BB of the else branch
            return else_bb
        elif else_bb is None:
            # Else branch jumps: We continue in the BB of the if branch
            return if_bb
        else:
            # No branch jumps: We have to merge the control flow
            return self.cfg.new_bb(if_bb, else_bb)

    def visit_While(self, node: ast.While, bb: BB, jumps: Jumps) -> Optional[BB]:
        head_bb = self.cfg.new_bb(bb)
        body_bb = self.cfg.new_bb(head_bb)
        tail_bb = self.cfg.new_bb(head_bb)
        head_bb.branch_pred = node.test

        new_jumps = Jumps(
            return_bb=jumps.return_bb, continue_bb=head_bb, break_bb=tail_bb
        )
        body_bb = self.visit_stmts(node.body, body_bb, new_jumps)

        if body_bb is None:
            # This happens if the loop body always returns. We continue with tail_bb
            # nonetheless since the loop condition could be false for the first
            # iteration, so it's not a guaranteed return
            return tail_bb

        # Otherwise, jump back to the head and continue compilation in the tail.
        self.cfg.link(body_bb, head_bb)
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
        self.cfg.link(bb, jumps.return_bb)
        bb.statements.append(node)
        return None

    def visit_Pass(self, node: ast.Pass, bb: BB, jumps: Jumps) -> Optional[BB]:
        return bb

    def generic_visit(self, node: ast.AST, bb: BB, jumps: Jumps) -> Optional[BB]:  # type: ignore
        # All other statements are blindly added to the BB
        assert isinstance(node, ast.stmt)
        bb.statements.append(node)
        return bb


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
