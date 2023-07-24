import ast
from dataclasses import dataclass, field
from typing import Optional, Sequence

from guppy.ast_util import AstNode, name_nodes_in_ast
from guppy.compiler_base import RawVariable, return_var


@dataclass
class VariableStats:
    """Stores program analysis results for a basic block.

    This class carries the results of live variable, definite assignment, and maybe
    assignment analysis.
    """

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


VarRow = Sequence[RawVariable]


@dataclass(frozen=True)
class Signature:
    """The signature of a basic block.

    Stores the inout/output variables with their types.
    """

    input_row: VarRow
    output_rows: Sequence[VarRow]  # One for each successor


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

    # Information about assigned/used variables in the BB
    _vars: Optional[VariableStats] = None

    @property
    def vars(self) -> VariableStats:
        """Returns information about the assigned/used variables in this BB.

        Note that `compute_variable_stats` must be called before this property can be
        accessed.
        """
        assert self._vars is not None
        return self._vars

    def compute_variable_stats(self, num_returns: int) -> None:
        """Determines which variables are assigned/used in this BB.

        This also requires the expected number of returns of the whole CFG in order to
        process `return` statements.
        """
        visitor = VariableVisitor(self, num_returns)
        for s in self.statements:
            visitor.visit(s)
        self._vars = visitor.stats

        if self.branch_pred is not None:
            self._vars.update_used(self.branch_pred)

        # In the `StatementCompiler`, we're going to turn return statements into
        # assignments of dummy variables `%ret_xxx`. Thus, we have to register those
        # variables as being used in the exit BB
        if len(self.successors) == 0:
            self._vars.used |= {
                return_var(i): ast.Name(return_var(i), ast.Load)
                for i in range(num_returns)
            }


class VariableVisitor(ast.NodeVisitor):
    """Visitor that computes used and assigned variables in a BB."""

    bb: BB
    stats: VariableStats
    num_returns: int

    def __init__(self, bb: BB, num_returns: int):
        self.bb = bb
        self.num_returns = num_returns
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

    def visit_Return(self, node: ast.Return) -> None:
        if node.value is not None:
            self.stats.update_used(node.value)

        # In the `StatementCompiler`, we're going to turn return statements into
        # assignments of dummy variables `%ret_xxx`. To make the liveness analysis work,
        # we have to register those variables as being assigned here
        self.stats.assigned |= {return_var(i): node for i in range(self.num_returns)}
        return None

    def generic_visit(self, node: ast.AST) -> None:
        self.stats.update_used(node)
