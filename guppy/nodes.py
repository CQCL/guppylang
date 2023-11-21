"""Custom AST nodes used by Guppy"""

import ast
from typing import TYPE_CHECKING, Any, Mapping

from guppy.guppy_types import FunctionType

if TYPE_CHECKING:
    from guppy.cfg.cfg import CFG
    from guppy.checker.core import Variable, CallableVariable
    from guppy.checker.cfg_checker import CheckedCFG


class LocalName(ast.expr):
    id: str

    _fields = ("id",)


class GlobalName(ast.expr):
    id: str
    value: "Variable"

    _fields = (
        "id",
        "value",
    )


class LocalCall(ast.expr):
    func: ast.expr
    args: list[ast.expr]

    _fields = (
        "func",
        "args",
    )


class GlobalCall(ast.expr):
    func: "CallableVariable"
    args: list[ast.expr]

    # Later: Inferred type args

    _fields = (
        "func",
        "args",
    )


class NestedFunctionDef(ast.FunctionDef):
    cfg: "CFG"
    ty: FunctionType

    def __init__(self, cfg: "CFG", ty: FunctionType, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.cfg = cfg
        self.ty = ty


class CheckedNestedFunctionDef(ast.FunctionDef):
    cfg: "CheckedCFG"
    ty: FunctionType
    captured: Mapping[str, "Variable"]

    def __init__(
        self,
        cfg: "CheckedCFG",
        ty: FunctionType,
        captured: Mapping[str, "Variable"],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.cfg = cfg
        self.ty = ty
        self.captured = captured
