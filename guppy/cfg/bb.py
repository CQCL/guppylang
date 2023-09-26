import ast
from dataclasses import dataclass, field
from typing import Optional, Sequence, TYPE_CHECKING, Union, Any

from guppy.ast_util import AstNode, name_nodes_in_ast
from guppy.compiler_base import RawVariable, return_var
from guppy.guppy_types import FunctionType
from guppy.hugr.hugr import CFNode

if TYPE_CHECKING:
    from guppy.cfg.cfg import CFG


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


VarRow = Sequence[RawVariable]


@dataclass(frozen=True)
class Signature:
    """The signature of a basic block.

    Stores the inout/output variables with their types.
    """

    input_row: VarRow
    output_rows: Sequence[VarRow]  # One for each successor


@dataclass(frozen=True)
class CompiledBB:
    """The result of compiling a basic block.

    Besides the corresponding node in the graph, we also store the signature of the
    basic block with type information.
    """

    node: CFNode
    bb: "BB"
    sig: Signature


class NestedFunctionDef(ast.FunctionDef):
    cfg: "CFG"
    ty: FunctionType

    def __init__(self, cfg: "CFG", ty: FunctionType, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.cfg = cfg
        self.ty = ty


BBStatement = Union[ast.Assign, ast.AugAssign, ast.Expr, ast.Return, NestedFunctionDef]


@dataclass(eq=False)  # Disable equality to recover hash from `object`
class BB:
    """A basic block in a control flow graph."""

    idx: int

    # Pointer to the CFG that contains this node
    cfg: "CFG"

    # AST statements contained in this BB
    statements: list[BBStatement] = field(default_factory=list)

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
        """Returns variable usage information for this BB.

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

    def visit_NestedFunctionDef(self, node: NestedFunctionDef) -> None:
        # In order to compute the used external variables in a nested function
        # definition, we have to run live variable analysis first
        from guppy.cfg.analysis import LivenessAnalysis

        for bb in node.cfg.bbs:
            bb.compute_variable_stats(len(node.ty.returns))
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
