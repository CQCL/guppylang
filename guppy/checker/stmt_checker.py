"""Type checking code for statements.

Operates on statements in a basic block after CFG construction. In particular, we
assume that statements involving control flow (i.e. if, while, break, and return
statements) have been removed during CFG construction.

After checking, we return a desugared statement where all sub-expression have beem type
annotated.
"""

import ast
from typing import Sequence

from guppy.ast_util import with_loc, AstVisitor
from guppy.cfg.bb import BB, BBStatement
from guppy.checker.core import Variable, Context
from guppy.checker.expr_checker import ExprSynthesizer, ExprChecker
from guppy.error import GuppyError, GuppyTypeError, InternalGuppyError
from guppy.gtypes import GuppyType, TupleType, type_from_ast, NoneType, Subst
from guppy.nodes import NestedFunctionDef


class StmtChecker(AstVisitor[BBStatement]):
    ctx: Context
    bb: BB
    return_ty: GuppyType

    def __init__(self, ctx: Context, bb: BB, return_ty: GuppyType) -> None:
        assert not return_ty.free_vars
        self.ctx = ctx
        self.bb = bb
        self.return_ty = return_ty

    def check_stmts(self, stmts: Sequence[BBStatement]) -> list[BBStatement]:
        return [self.visit(s) for s in stmts]

    def _synth_expr(self, node: ast.expr) -> tuple[ast.expr, GuppyType]:
        return ExprSynthesizer(self.ctx).synthesize(node)

    def _check_expr(
        self, node: ast.expr, ty: GuppyType, kind: str = "expression"
    ) -> tuple[ast.expr, Subst]:
        return ExprChecker(self.ctx).check(node, ty, kind)

    def _check_assign(self, lhs: ast.expr, ty: GuppyType, node: ast.stmt) -> None:
        """Helper function to check assignments with patterns."""
        # Easiest case is if the LHS pattern is a single variable.
        if isinstance(lhs, ast.Name):
            # Check if we override an unused linear variable
            x = lhs.id
            if x in self.ctx.locals:
                var = self.ctx.locals[x]
                if var.ty.linear and var.used is None:
                    raise GuppyError(
                        f"Variable `{x}` with linear type `{var.ty}` is not used",
                        var.defined_at,
                    )
            self.ctx.locals[x] = Variable(x, ty, node, None)
        # The only other thing we support right now are tuples
        elif isinstance(lhs, ast.Tuple):
            tys = ty.element_types if isinstance(ty, TupleType) else [ty]
            n, m = len(lhs.elts), len(tys)
            if n != m:
                raise GuppyTypeError(
                    f"{'Too many' if n < m else 'Not enough'} values to unpack "
                    f"(expected {n}, got {m})",
                    node,
                )
            for pat, el_ty in zip(lhs.elts, tys):
                self._check_assign(pat, el_ty, node)
        # TODO: Python also supports assignments like `[a, b] = [1, 2]` or
        #  `a, *b = ...`. The former would require some runtime checks but
        #  the latter should be easier to do (unpack and repack the rest).
        else:
            raise GuppyError("Assignment pattern not supported", lhs)

    def visit_Assign(self, node: ast.Assign) -> ast.stmt:
        if len(node.targets) > 1:
            # This is the case for assignments like `a = b = 1`
            raise GuppyError("Multi assignment not supported", node)

        [target] = node.targets
        node.value, ty = self._synth_expr(node.value)
        self._check_assign(target, ty, node)
        return node

    def visit_AnnAssign(self, node: ast.AnnAssign) -> ast.stmt:
        if node.value is None:
            raise GuppyError(
                "Variable declaration is not supported. Assignment is required", node
            )
        ty = type_from_ast(node.annotation, self.ctx.globals)
        node.value, subst = self._check_expr(node.value, ty)
        assert not ty.free_vars and len(subst) == 0  # `ty` must be closed!
        self._check_assign(node.target, ty, node)
        return node

    def visit_AugAssign(self, node: ast.AugAssign) -> ast.stmt:
        bin_op = with_loc(
            node, ast.BinOp(left=node.target, op=node.op, right=node.value)
        )
        assign = with_loc(node, ast.Assign(targets=[node.target], value=bin_op))
        return self.visit_Assign(assign)

    def visit_Expr(self, node: ast.Expr) -> ast.stmt:
        # An expression statement where the return value is discarded
        node.value, ty = self._synth_expr(node.value)
        if ty.linear:
            raise GuppyTypeError(f"Value with linear type `{ty}` is not used", node)
        return node

    def visit_Return(self, node: ast.Return) -> ast.stmt:
        if node.value is not None:
            node.value, subst = self._check_expr(
                node.value, self.return_ty, "return value"
            )
            assert len(subst) == 0  # `self.return_ty` is closed!
        elif not isinstance(self.return_ty, NoneType):
            raise GuppyTypeError(
                f"Expected return value of type `{self.return_ty}`", None
            )
        return node

    def visit_NestedFunctionDef(self, node: NestedFunctionDef) -> ast.stmt:
        from guppy.checker.func_checker import check_nested_func_def

        func_def = check_nested_func_def(node, self.bb, self.ctx)
        self.ctx.locals[func_def.name] = Variable(
            func_def.name, func_def.ty, func_def, None
        )
        return func_def

    def visit_If(self, node: ast.If) -> None:
        raise InternalGuppyError("Control-flow statement should not be present here.")

    def visit_While(self, node: ast.While) -> None:
        raise InternalGuppyError("Control-flow statement should not be present here.")

    def visit_Break(self, node: ast.Break) -> None:
        raise InternalGuppyError("Control-flow statement should not be present here.")

    def visit_Continue(self, node: ast.Continue) -> None:
        raise InternalGuppyError("Control-flow statement should not be present here.")
