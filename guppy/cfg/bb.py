import ast
from abc import ABC
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING, Union
from typing_extensions import Self

from guppy.ast_util import AstNode, name_nodes_in_ast
from guppy.nodes import NestedFunctionDef

if TYPE_CHECKING:
    from guppy.cfg.cfg import BaseCFG


@dataclass
class VariableStats:
    """Stores variable usage information for a basic block."""

    # Variables that are assigned in the BB
    assigned: dict[str, AstNode] = field(default_factory=dict)

    # The (external) variables used in the BB, i.e. usages of variables that are
    # assigned in the BB are not included here.
    used: dict[str, ast.Name] = field(default_factory=dict)

    def update_used(self, node: ast.AST) -> None:
        """Marks the variables occurring in a statement as used.

        This method should be called whenever an expression is used in the BB.
        """
        for name in name_nodes_in_ast(node):
            # Should point to first use, so also check that the name is not already
            # contained
            if name.id not in self.assigned and name.id not in self.used:
                self.used[name.id] = name


BBStatement = Union[ast.Assign, ast.AugAssign, ast.AnnAssign, ast.Expr, ast.Return, NestedFunctionDef]


@dataclass(eq=False)  # Disable equality to recover hash from `object`
class BB(ABC):
    """A basic block in a control flow graph."""

    idx: int

    # Pointer to the CFG that contains this node
    cfg: "BaseCFG[Self]"

    # AST statements contained in this BB
    statements: list[BBStatement] = field(default_factory=list)

    # Predecessor and successor BBs
    predecessors: list[Self] = field(default_factory=list)
    successors: list[Self] = field(default_factory=list)

    # If the BB has multiple successors, we need a predicate to decide to which one to
    # jump to
    branch_pred: Optional[ast.expr] = None

    # Information about assigned/used variables in the BB
    _vars: Optional[VariableStats] = None

    @property
    def vars(self) -> VariableStats:
        """Returns variable usage information for this BB.

        Note that `compute_variable_stats` must be called before this property can be
        accessed.
        """
        assert self._vars is not None
        return self._vars

    def compute_variable_stats(self) -> None:
        """Determines which variables are assigned/used in this BB."""
        visitor = VariableVisitor(self)
        for s in self.statements:
            visitor.visit(s)
        self._vars = visitor.stats

        if self.branch_pred is not None:
            self._vars.update_used(self.branch_pred)


class VariableVisitor(ast.NodeVisitor):
    """Visitor that computes used and assigned variables in a BB."""

    bb: BB
    stats: VariableStats

    def __init__(self, bb: BB):
        self.bb = bb
        self.stats = VariableStats()

    def visit_Assign(self, node: ast.Assign) -> None:
        self.stats.update_used(node.value)
        for t in node.targets:
            for name in name_nodes_in_ast(t):
                self.stats.assigned[name.id] = node

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self.stats.update_used(node.value)
        self.stats.update_used(node.target)  # The target is also used
        for name in name_nodes_in_ast(node.target):
            self.stats.assigned[name.id] = node

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value:
            self.stats.update_used(node.value)
        for name in name_nodes_in_ast(node.target):
            self.stats.assigned[name.id] = node

    def visit_NestedFunctionDef(self, node: NestedFunctionDef) -> None:
        # In order to compute the used external variables in a nested function
        # definition, we have to run live variable analysis first
        from guppy.cfg.analysis import LivenessAnalysis

        for bb in node.cfg.bbs:
            bb.compute_variable_stats()
        live = LivenessAnalysis().run(node.cfg.bbs)

        # Only store used *external* variables: things defined in the current BB, as
        # well as the function name and argument names should not be included
        assigned_before_in_bb = (
            self.stats.assigned.keys()
            | {node.name}
            | set(a.arg for a in node.args.args)
        )
        self.stats.used |= {
            x: using_bb.vars.used[x]
            for x, using_bb in live[node.cfg.entry_bb].items()
            if x not in assigned_before_in_bb
        }

        # The name of the function is now assigned
        self.stats.assigned[node.name] = node

    def generic_visit(self, node: ast.AST) -> None:
        self.stats.update_used(node)
