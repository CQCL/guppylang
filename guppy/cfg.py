import ast
from dataclasses import dataclass, field
from typing import Optional

from guppy.free_names import name_nodes_in_ast
from guppy.util import Assign, InternalGuppyError, GuppyError
from guppy.visitor import AstVisitor


@dataclass
class VarAnalysis:
    # Variables that are assigned in the BB
    assigned: dict[str, Assign] = field(default_factory=dict)

    # The (external) variables used in the BB, i.e. usages of variables that are
    # assigned in the BB are not included here.
    used: dict[str, ast.Name] = field(default_factory=dict)

    # Variables that are live before the execution of the BB. We store the BB in which
    # the use occurs as evidence of liveness
    live_before: dict[str, "BB"] = field(default_factory=dict)

    # Variables that are definitely assigned before the execution of the BB
    assigned_before: set[str] = field(default_factory=set)


@dataclass(eq=False)  # Disable equality to recover hash from `object`
class BB:
    """A basic block in a control flow graph."""

    idx: int

    # AST statements contained in this BB
    statements: list[ast.stmt] = field(default_factory=list)

    # Predecessor and successor BBs
    predecessors: list["BB"] = field(default_factory=list)
    successors: list["BB"] = field(default_factory=list)

    # If the BB has multiple successors, we need a predicate to decide to which one to
    # jump to
    branch_pred: Optional[ast.expr] = None

    # Program analysis data
    vars: VarAnalysis = field(default_factory=VarAnalysis)


class FunctionalBB(BB):
    """A basic block that is compiled via a functional node.

    We turn loops and if-statements that are annotated with `_@functional` into CFGs.
    This allows us to reuse the liveness and definite assignment analysis code. When
    compiling the CFG, we turn those functional BBs back into dataflow nodes and attach
    them to the predecessor BB.
    """


class FunctionalBranchBB(FunctionalBB):
    """A basic block that does functional branching."""


class FunctionalMergeBB(FunctionalBB):
    """A basic block that merges a functional branch."""


class FunctionalLoopBB(FunctionalBB):
    """A basic block that starts a functional loop."""


@dataclass
class CFG:
    bbs: list[BB] = field(default_factory=list)

    def __post_init__(self):
        self.entry_bb = self.new_bb()
        self.exit_bb = self.new_bb()

    def new_bb(self, pred: Optional[BB] = None, preds: Optional[list[BB]] = None):
        preds = preds if preds is not None else [pred] if pred is not None else []
        bb = BB(len(self.bbs), predecessors=preds)
        self.bbs.append(bb)
        for p in preds:
            p.successors.append(bb)
        return bb

    def link(self, src_bb: BB, tgt_bb: BB):
        src_bb.successors.append(tgt_bb)
        tgt_bb.predecessors.append(src_bb)

    def analyze_liveness(self):
        for bb in self.bbs:
            bb.vars.live_before = dict()
        self.exit_bb.vars.live_before = {x: self.exit_bb for x in self.exit_bb.vars.used}
        queue = set(self.bbs)
        while len(queue) > 0:
            bb = queue.pop()
            for pred in bb.predecessors:
                live_before = {x: pred for x in pred.vars.used} | {
                    x: b
                    for x, b in bb.vars.live_before.items()
                    if x not in pred.vars.assigned.keys()
                }
                if not set.issubset(set(live_before.keys()), pred.vars.live_before.keys()):
                    pred.vars.live_before |= live_before
                    queue.add(pred)

    def analyze_definite_assignment(self):
        all_vars = set.union(*(bb.vars.used.keys() | bb.vars.assigned.keys() for bb in self.bbs))
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

    def remove_empty_bbs(self):
        new_bbs = []
        for bb in self.bbs:
            if (
                len(bb.statements) == 0
                and bb.branch_pred is None
                and bb not in (self.entry_bb, self.exit_bb)
            ):
                succ = bb.successors[0]
                succ.predecessors.remove(bb)
                for pred in bb.predecessors:
                    pred.successors[pred.successors.index(bb)] = succ
                    succ.predecessors.append(pred)
            else:
                new_bbs.append(bb)
        self.bbs = new_bbs


def return_var(n: int) -> str:
    return f"%ret{n}"


@dataclass(frozen=True)
class Jumps:
    return_bb: BB
    continue_bb: Optional[BB]
    break_bb: Optional[BB]


class CFGBuilder(AstVisitor[Optional[BB]]):
    cfg: CFG
    num_returns: int

    def build(self, nodes: list[ast.stmt], num_returns: int) -> CFG:
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
                raise NotImplementedError()
                assert_no_jumps(node)
                bb.statements.append(node)
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


class JumpDetector(ast.NodeVisitor):
    def visit_Break(self, node: ast.Break) -> None:
        raise GuppyError("Break is not allowed in a functional statement", node)

    def visit_Continue(self, node: ast.Continue) -> None:
        raise GuppyError("Break is not allowed in a functional statement", node)

    def visit_Return(self, node: ast.Return) -> None:
        raise GuppyError("Break is not allowed in a functional statement", node)

    def visit_Expr(self, node: ast.Expr) -> None:
        if is_functional_annotation(node):
            raise GuppyError("Statement already contained in a functional block", node)


def assert_no_jumps(node: ast.AST) -> None:
    d = JumpDetector()
    d.visit(node)
