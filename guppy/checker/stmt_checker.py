"""Type checking code for statements.

Operates on statements in a basic block after CFG construction. In particular, we
assume that statements involving control flow (i.e. if, while, break, and return
statements) have been removed during CFG construction.

After checking, we return a desugared statement where all sub-expression have been type
annotated.
"""

import ast
from collections.abc import Sequence

from guppy.ast_util import AstVisitor, with_loc
from guppy.cfg.bb import BB, BBStatement
from guppy.checker.core import Context, Variable
from guppy.checker.expr_checker import ExprChecker, ExprSynthesizer
from guppy.error import GuppyError, GuppyTypeError, InternalGuppyError
from guppy.gtypes import GuppyType, NoneType, TupleType, type_from_ast
from guppy.nodes import NestedFunctionDef


class StmtChecker(AstVisitor[BBStatement]):
    ctx: Context
    bb: BB
    return_ty: GuppyType

    def __init__(self, ctx: Context, bb: BB, return_ty: GuppyType) -> None:
        self.ctx = ctx
        self.bb = bb
        self.return_ty = return_ty

    def check_stmts(self, stmts: Sequence[BBStatement]) -> list[BBStatement]:
        return [self.visit(s) for s in stmts]

    def _synth_expr(self, node: ast.expr) -> tuple[ast.expr, GuppyType]:
        return ExprSynthesizer(self.ctx).synthesize(node)

    def _check_expr(
        self, node: ast.expr, ty: GuppyType, kind: str = "expression"
    ) -> ast.expr:
        return ExprChecker(self.ctx).check(node, ty, kind)

    def _check_assign(self, lhs: ast.expr, ty: GuppyType, node: ast.stmt) -> None:
        """Helper function to check assignments with patterns."""
        match lhs:
            # Easiest case is if the LHS pattern is a single variable.
            case ast.Name(id=x):
                # Check if we override an unused linear variable
                if x in self.ctx.locals:
                    var = self.ctx.locals[x]
                    if var.ty.linear and var.used is None:
                        msg = f"Variable `{x}` with linear type `{var.ty}` is not used"
                        raise GuppyError(
                            msg,
                            var.defined_at,
                        )
                self.ctx.locals[x] = Variable(x, ty, node, None)

            # The only other thing we support right now are tuples
            case ast.Tuple(elts=elts):
                tys = ty.element_types if isinstance(ty, TupleType) else [ty]
                n, m = len(elts), len(tys)
                if n != m:
                    msg = (
                        f"{'Too many' if n < m else 'Not enough'} values to unpack "
                        f"(expected {n}, got {m})"
                    )
                    raise GuppyTypeError(
                        msg,
                        node,
                    )
                for pat, el_ty in zip(elts, tys):
                    self._check_assign(pat, el_ty, node)

            # TODO: Python also supports assignments like `[a, b] = [1, 2]` or
            #  `a, *b = ...`. The former would require some runtime checks but
            #  the latter should be easier to do (unpack and repack the rest).
            case _:
                msg = "Assignment pattern not supported"
                raise GuppyError(msg, lhs)

    def visit_Assign(self, node: ast.Assign) -> ast.stmt:
        if len(node.targets) > 1:
            # This is the case for assignments like `a = b = 1`
            msg = "Multi assignment not supported"
            raise GuppyError(msg, node)

        [target] = node.targets
        node.value, ty = self._synth_expr(node.value)
        self._check_assign(target, ty, node)
        return node

    def visit_AnnAssign(self, node: ast.AnnAssign) -> ast.stmt:
        if node.value is None:
            msg = "Variable declaration is not supported. Assignment is required"
            raise GuppyError(
                msg, node
            )
        ty = type_from_ast(node.annotation, self.ctx.globals)
        node.value = self._check_expr(node.value, ty)
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
            msg = f"Value with linear type `{ty}` is not used"
            raise GuppyTypeError(msg, node)
        return node

    def visit_Return(self, node: ast.Return) -> ast.stmt:
        if node.value is not None:
            node.value = self._check_expr(node.value, self.return_ty, "return value")
        elif not isinstance(self.return_ty, NoneType):
            msg = f"Expected return value of type `{self.return_ty}`"
            raise GuppyTypeError(
                msg, None
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
        msg = "Control-flow statement should not be present here."
        raise InternalGuppyError(msg)

    def visit_While(self, node: ast.While) -> None:
        msg = "Control-flow statement should not be present here."
        raise InternalGuppyError(msg)

    def visit_Break(self, node: ast.Break) -> None:
        msg = "Control-flow statement should not be present here."
        raise InternalGuppyError(msg)

    def visit_Continue(self, node: ast.Continue) -> None:
        msg = "Control-flow statement should not be present here."
        raise InternalGuppyError(msg)
