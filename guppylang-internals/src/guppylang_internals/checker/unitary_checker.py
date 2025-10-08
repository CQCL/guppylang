import ast
from typing import Any

from guppylang_internals.ast_util import get_type
from guppylang_internals.checker.cfg_checker import CheckedBB, CheckedCFG
from guppylang_internals.checker.core import Place, contains_subscript
from guppylang_internals.checker.errors.generic import (
    InvalidUnderDagger,
    UnsupportedError,
)
from guppylang_internals.definition.value import CallableDef
from guppylang_internals.engine import ENGINE
from guppylang_internals.error import GuppyError, GuppyTypeError
from guppylang_internals.nodes import (
    AnyCall,
    BarrierExpr,
    GlobalCall,
    LocalCall,
    PlaceNode,
    ResultExpr,
    StateResultExpr,
    TensorCall,
)
from guppylang_internals.tys.errors import UnitaryCallError
from guppylang_internals.tys.qubit import contain_qubit_ty
from guppylang_internals.tys.ty import FunctionType, UnitaryFlags


class BBUnitaryChecker(ast.NodeVisitor):
    flags: UnitaryFlags

    """AST visitor that checks whether the modifiers (dagger, control, power)
    are applicable."""

    def check(self, bb: CheckedBB[Place], unitary_flags: UnitaryFlags) -> None:
        self.flags = unitary_flags
        for stmt in bb.statements:
            self.visit(stmt)

    def _check_classical_args(self, args: list[ast.expr]) -> bool:
        for arg in args:
            self.visit(arg)
            if contain_qubit_ty(get_type(arg)):
                return False
        return True

    def _check_call(self, node: AnyCall, ty: FunctionType) -> None:
        classic = self._check_classical_args(node.args)
        flag_ok = self.flags in ty.unitary_flags
        if not classic and not flag_ok:
            raise GuppyTypeError(
                UnitaryCallError(node, self.flags & (~ty.unitary_flags))
            )

    def visit_GlobalCall(self, node: GlobalCall) -> None:
        func = ENGINE.get_parsed(node.def_id)
        assert isinstance(func, CallableDef)
        self._check_call(node, func.ty)

    def visit_LocalCall(self, node: LocalCall) -> None:
        func = get_type(node.func)
        assert isinstance(func, FunctionType)
        self._check_call(node, func)

    def visit_TensorCall(self, node: TensorCall) -> None:
        self._check_call(node, node.tensor_ty)

    def visit_BarrierExpr(self, node: BarrierExpr) -> None:
        # Barrier is always allowed
        pass

    def visit_ResultExpr(self, node: ResultExpr) -> None:
        # Result is always allowed
        pass

    def visit_StateResultExpr(self, node: StateResultExpr) -> None:
        # StateResult is always allowed
        pass

    def _check_assign(self, node: Any) -> None:
        assert isinstance(node, ast.Assign | ast.AnnAssign | ast.AugAssign)
        if UnitaryFlags.Dagger in self.flags:
            raise GuppyError(InvalidUnderDagger(node, "Assignment"))
        if node.value is not None:
            self.visit(node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._check_assign(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        self._check_assign(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self._check_assign(node)

    def visit_For(self, node: ast.For) -> None:
        if UnitaryFlags.Dagger in self.flags:
            raise GuppyError(InvalidUnderDagger(node, "Loop"))
        self.generic_visit(node)

    def visit_PlaceNode(self, node: PlaceNode) -> None:
        if UnitaryFlags.Dagger in self.flags and contains_subscript(node.place):
            raise GuppyError(
                UnsupportedError(node, "index access", True, "dagger context")
            )


def check_cfg_unitary(
    cfg: CheckedCFG[Place],
    unitary_flags: UnitaryFlags,
) -> None:
    bb_checker = BBUnitaryChecker()
    for bb in cfg.bbs:
        bb_checker.check(bb, unitary_flags)
