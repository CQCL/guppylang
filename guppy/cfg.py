import ast
from dataclasses import dataclass, field
from typing import Optional, NamedTuple

from guppy.bb import BB, CompiledBB
from guppy.compiler_base import Signature, return_var, VarMap
from guppy.error import InternalGuppyError, GuppyError
from guppy.ast_util import AstVisitor, name_nodes_in_ast, line_col
from guppy.guppy_types import GuppyType
from guppy.hugr.hugr import Node, Hugr


@dataclass
class CFG:
    """A control-flow graph."""

    bbs: list[BB] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.entry_bb = self.new_bb()
        self.exit_bb = self.new_bb()

    def new_bb(self, pred: Optional[BB] = None, preds: Optional[list[BB]] = None) -> BB:
        """Adds a new basic block to the CFG.

        Optionally, a single predecessor or a list of predecessor BBs can be passed.
        """
        preds = preds if preds is not None else [pred] if pred is not None else []
        bb = BB(len(self.bbs), predecessors=preds)
        self.bbs.append(bb)
        for p in preds:
            p.successors.append(bb)
        return bb

    def link(self, src_bb: BB, tgt_bb: BB) -> None:
        """Adds a control-flow edge between two basic blocks."""
        src_bb.successors.append(tgt_bb)
        tgt_bb.predecessors.append(src_bb)

    def _analyze_liveness(self) -> None:
        """Runs live variable analysis."""
        for bb in self.bbs:
            bb.vars.live_before = dict()
        self.exit_bb.vars.live_before = {
            x: self.exit_bb for x in self.exit_bb.vars.used
        }
        queue = set(self.bbs)
        while len(queue) > 0:
            bb = queue.pop()
            for pred in bb.predecessors:
                live_before = {x: pred for x in pred.vars.used} | {
                    x: b
                    for x, b in bb.vars.live_before.items()
                    if x not in pred.vars.assigned.keys()
                }
                if not set.issubset(
                    set(live_before.keys()), pred.vars.live_before.keys()
                ):
                    pred.vars.live_before |= live_before
                    queue.add(pred)

    def _analyze_definite_assignment(self) -> None:
        """Runs definite assignment analysis."""
        all_vars = set.union(
            *(bb.vars.used.keys() | bb.vars.assigned.keys() for bb in self.bbs)
        )
        for bb in self.bbs:
            bb.vars.assigned_before = all_vars.copy()
        self.entry_bb.vars.assigned_before = set()
        queue = set(self.bbs)
        while len(queue) > 0:
            bb = queue.pop()
            assigned_after = bb.vars.assigned_before | bb.vars.assigned.keys()
            for succ in bb.successors:
                if not set.issubset(succ.vars.assigned_before, assigned_after):
                    succ.vars.assigned_before &= assigned_after
                    queue.add(succ)

    def _analyze_maybe_assignment(self) -> None:
        """Runs maybe assignment analysis.

        This computes the variables that *might* be defined at every program point but
        are not guaranteed to be assigned. I.e. a variable that is defined on some paths
        but not on all paths.
        Note that this pass uses the results from the definite assignment analysis, so
        it must be run afterward.
        """
        for bb in self.bbs:
            bb.vars.maybe_assigned_before = set()
        queue = set(self.bbs)
        while len(queue) > 0:
            bb = queue.pop()
            maybe_ass_after = bb.vars.maybe_assigned_before | bb.vars.assigned.keys()
            for succ in bb.successors:
                maybe_ass = maybe_ass_after - succ.vars.assigned_before
                if not set.issubset(maybe_ass, succ.vars.maybe_assigned_before):
                    succ.vars.maybe_assigned_before |= maybe_ass
                    queue.add(succ)

    def analyze(self) -> None:
        """Runs all program analysis passes."""
        self._analyze_liveness()
        self._analyze_definite_assignment()
        self._analyze_maybe_assignment()

    def compile(
        self,
        graph: Hugr,
        input_sig: Signature,
        return_tys: list[GuppyType],
        parent: Node,
        global_variables: VarMap,
    ) -> None:
        """Compiles the CFG."""

        compiled: dict[BB, CompiledBB] = {}

        entry_compiled = self.entry_bb.compile(
            graph, input_sig, return_tys, parent, global_variables
        )
        compiled[self.entry_bb] = entry_compiled

        # Visit all control-flow edges in BFS order
        stack = [
            (entry_compiled, entry_compiled.output_sigs[i], succ)
            # Put successors onto stack in reverse order to maintain the original order
            # when popping
            for i, succ in reversed(list(enumerate(self.entry_bb.successors)))
        ]
        while len(stack) > 0:
            pred, sig, bb = stack.pop()

            # If the BB was already compiled, we just have to check that the signatures
            # match.
            if bb in compiled:
                assert len(sig) == len(compiled[bb].input_sig)
                for v1, v2 in zip(sig, compiled[bb].input_sig):
                    assert v1.name == v2.name
                    if v1.ty != v2.ty:
                        # Sort defined locations by line and column
                        d1 = sorted(v1.defined_at, key=line_col)
                        d2 = sorted(v2.defined_at, key=line_col)
                        [(v1, d1), (v2, d2)] = sorted(
                            [(v1, d1), (v2, d2)], key=lambda x: line_col(x[1][0])
                        )
                        f1 = [f"{{{i}}}" for i in range(len(d1))]
                        f2 = [f"{{{len(f1) + i}}}" for i in range(len(d2))]
                        raise GuppyError(
                            f"Variable `{v1.name}` can refer to different types: "
                            f"`{v1.ty}` (at {', '.join(f1)}) vs "
                            f"`{v2.ty}` (at {', '.join(f2)})",
                            bb.vars.live_before[v1.name].vars.used[v1.name],
                            d1 + d2,
                        )
                graph.add_edge(
                    pred.node.add_out_port(), compiled[bb].node.in_port(None)
                )

            # Otherwise, compile the BB and put successors on the stack
            else:
                bb_compiled = bb.compile(
                    graph, sig, return_tys, parent, global_variables
                )
                graph.add_edge(pred.node.add_out_port(), bb_compiled.node.in_port(None))
                compiled[bb] = bb_compiled
                stack += [
                    (bb_compiled, bb_compiled.output_sigs[i], succ)
                    # Put successors onto stack in reverse order to maintain the
                    # original order when popping
                    for i, succ in reversed(list(enumerate(bb.successors)))
                ]


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

        # In the main `BBCompiler`, we're going to turn return statements into
        # assignments of dummy variables `%ret_xxx`. To make the liveness analysis work,
        # we have to register those variables as being used in the exit BB
        self.cfg.exit_bb.vars.used = {return_var(i): None for i in range(num_returns)}  # type: ignore

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

    def _update_used(self, bb: BB, expr: ast.expr) -> None:
        for name in name_nodes_in_ast(expr):
            # Should point to first use, so also check that the name is not already
            # contained
            if name.id not in bb.vars.assigned and name.id not in bb.vars.used:
                bb.vars.used[name.id] = name

    def visit_Assign(self, node: ast.Assign, bb: BB, jumps: Jumps) -> Optional[BB]:
        bb.statements.append(node)
        self._update_used(bb, node.value)
        for t in node.targets:
            for name in name_nodes_in_ast(t):
                bb.vars.assigned[name.id] = node
        return bb

    def visit_AugAssign(
        self, node: ast.AugAssign, bb: BB, jumps: Jumps
    ) -> Optional[BB]:
        bb.statements.append(node)
        self._update_used(bb, node.value)
        self._update_used(bb, node.target)  # The target is also used
        for name in name_nodes_in_ast(node.target):
            bb.vars.assigned[name.id] = node
        return bb

    def visit_If(self, node: ast.If, bb: BB, jumps: Jumps) -> Optional[BB]:
        bb.branch_pred = node.test
        self._update_used(bb, node.test)
        if_bb = self.visit_stmts(node.body, self.cfg.new_bb(pred=bb), jumps)
        else_bb = self.visit_stmts(node.orelse, self.cfg.new_bb(pred=bb), jumps)
        # We need to handle different cases depending on whether branches jump (i.e.
        # return, continue, or break)
        if if_bb is None and else_bb is None:
            # Both jump: This means the whole if-statement jumps, so we don't have to do
            # anything
            return None
        elif if_bb is None:
            # If branch jumps: We continue in the BB of the else branch
            return else_bb
        elif else_bb is None:
            # Else branch jumps: We continue in the BB of the if branch
            return if_bb
        else:
            # No branch jumps: We have to merge the control flow
            return self.cfg.new_bb(preds=[if_bb, else_bb])

    def visit_While(self, node: ast.While, bb: BB, jumps: Jumps) -> Optional[BB]:
        head_bb = self.cfg.new_bb(pred=bb)
        body_bb, tail_bb = self.cfg.new_bb(pred=head_bb), self.cfg.new_bb(pred=head_bb)
        head_bb.branch_pred = node.test
        self._update_used(head_bb, node.test)

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
        if node.value is not None:
            self._update_used(bb, node.value)
        # In the main `BBCompiler`, we're going to turn return statements into
        # assignments of dummy variables `%ret_xxx`. To make the liveness analysis work,
        # we have to register those variables as being assigned here
        bb.vars.assigned |= {return_var(i): node for i in range(self.num_returns)}
        bb.statements.append(node)
        return None

    def visit_Pass(self, node: ast.Pass, bb: BB, jumps: Jumps) -> Optional[BB]:
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
