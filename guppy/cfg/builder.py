import ast
import itertools
from typing import Optional, Iterator, Union, NamedTuple

from guppy.ast_util import set_location_from, AstVisitor
from guppy.cfg.bb import BB, NestedFunctionDef
from guppy.cfg.cfg import CFG
from guppy.compiler_base import Globals
from guppy.error import GuppyError, InternalGuppyError


# In order to build expressions, need an endless stream of unique temporary variables
# to store intermediate results
tmp_vars: Iterator[str] = (f"%tmp{i}" for i in itertools.count())


class Jumps(NamedTuple):
    """Holds jump targets for return, continue, and break during CFG construction."""

    return_bb: BB
    continue_bb: Optional[BB]
    break_bb: Optional[BB]


class CFGBuilder(AstVisitor[Optional[BB]]):
    """Constructs a CFG from ast nodes."""

    cfg: CFG
    num_returns: int
    globals: Globals

    def build(self, nodes: list[ast.stmt], num_returns: int, globals: Globals) -> CFG:
        """Builds a CFG from a list of ast nodes.

        We also require the expected number of return ports for the whole CFG. This is
        needed to translate return statements into assignments of dummy return
        variables.
        """
        self.cfg = CFG()
        self.num_returns = num_returns
        self.globals = globals

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
        BranchBuilder.add_branch(node.test, self.cfg, bb, then_bb, else_bb)
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
        BranchBuilder.add_branch(node.test, self.cfg, head_bb, body_bb, tail_bb)

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

    def visit_FunctionDef(
        self, node: ast.FunctionDef, bb: BB, jumps: Jumps
    ) -> Optional[BB]:
        from guppy.function import FunctionDefCompiler

        func_ty = FunctionDefCompiler.validate_signature(node, self.globals)
        cfg = CFGBuilder().build(node.body, len(func_ty.returns), self.globals)

        new_node = NestedFunctionDef(
            cfg,
            func_ty,
            name=node.name,
            args=node.args,
            body=node.body,
            decorator_list=node.decorator_list,
            returns=node.returns,
            type_comment=node.type_comment,
        )
        set_location_from(new_node, node)
        bb.statements.append(new_node)
        return bb

    def generic_visit(self, node: ast.AST, bb: BB, jumps: Jumps) -> Optional[BB]:  # type: ignore
        # When adding support for new statements, we have to remember to use the
        # ExprBuilder to transform all included expressions!
        raise GuppyError("Statement is not supported", node)


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
        BranchBuilder.add_branch(node.test, self.cfg, self.bb, if_bb, else_bb)

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
            BranchBuilder.add_branch(node, self.cfg, self.bb, true_bb, false_bb)
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
    def add_branch(node: ast.expr, cfg: CFG, bb: BB, true_bb: BB, false_bb: BB) -> None:
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
    ) or (isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not))
