import ast
from dataclasses import dataclass

from guppy.ast_util import AstNode
from guppy.cfg.bb import BB
from guppy.checker.core import Globals, Context, CallableVariable
from guppy.checker.cfg_checker import CheckedCFG
from guppy.gtypes import FunctionType, GuppyType
from guppy.nodes import GlobalCall, CheckedNestedFunctionDef, NestedFunctionDef


@dataclass
class DefinedFunction(CallableVariable):
    """A user-defined function"""

    ty: FunctionType
    defined_at: ast.FunctionDef

    @staticmethod
    def from_ast(
        func_def: ast.FunctionDef, name: str, globals: Globals
    ) -> "DefinedFunction":
        ty = check_signature(func_def, globals)
        return DefinedFunction(name, ty, func_def, None)

    def check_call(
        self, args: list[ast.expr], ty: GuppyType, node: AstNode, ctx: Context
    ) -> GlobalCall:
        raise NotImplementedError

    def synthesize_call(
        self, args: list[ast.expr], node: AstNode, ctx: Context
    ) -> tuple[GlobalCall, GuppyType]:
        raise NotImplementedError


@dataclass
class CheckedFunction(DefinedFunction):
    """Type checked version of a user-defined function"""

    cfg: CheckedCFG


def check_global_func_def(func: DefinedFunction, globals: Globals) -> CheckedFunction:
    """Type checks a top-level function definition."""
    raise NotImplementedError


def check_nested_func_def(
    func_def: NestedFunctionDef, bb: BB, ctx: Context
) -> CheckedNestedFunctionDef:
    """Type checks a local (nested) function definition."""
    raise NotImplementedError


def check_signature(func_def: ast.FunctionDef, globals: Globals) -> FunctionType:
    """Checks the signature of a function definition and returns the corresponding
    Guppy type."""
    raise NotImplementedError
