import ast
from dataclasses import dataclass

from guppy.ast_util import return_nodes_in_ast, AstNode, with_loc
from guppy.cfg.bb import BB
from guppy.cfg.builder import CFGBuilder
from guppy.checker.core import Variable, Globals, Context, CallableVariable
from guppy.checker.cfg_checker import check_cfg, CheckedCFG
from guppy.checker.expr_checker import synthesize_call, check_call
from guppy.error import GuppyError
from guppy.types import FunctionType, type_from_ast, NoneType, GuppyType
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
        # Use default implementation from the expression checker
        args = check_call(self.ty, args, ty, node, ctx)
        return GlobalCall(func=self, args=args)

    def synthesize_call(
        self, args: list[ast.expr], node: AstNode, ctx: Context
    ) -> tuple[GlobalCall, GuppyType]:
        # Use default implementation from the expression checker
        args, ty = synthesize_call(self.ty, args, node, ctx)
        return GlobalCall(func=self, args=args), ty


@dataclass
class CheckedFunction(DefinedFunction):
    """Type checked version of a user-defined function"""

    cfg: CheckedCFG


def check_global_func_def(func: DefinedFunction, globals: Globals) -> CheckedFunction:
    """Type checks a top-level function definition."""
    func_def = func.defined_at
    args = func_def.args.args
    returns_none = isinstance(func.ty.returns, NoneType)
    assert func.ty.arg_names is not None

    cfg = CFGBuilder().build(func_def.body, returns_none, globals)
    inputs = [
        Variable(x, ty, loc, None)
        for x, ty, loc in zip(func.ty.arg_names, func.ty.args, args)
    ]
    cfg = check_cfg(cfg, inputs, func.ty.returns, globals)
    return CheckedFunction(func_def.name, func.ty, func_def, None, cfg)


def check_nested_func_def(
    func_def: NestedFunctionDef, bb: BB, ctx: Context
) -> CheckedNestedFunctionDef:
    """Type checks a local (nested) function definition."""
    func_ty = check_signature(func_def, ctx.globals)
    assert func_ty.arg_names is not None

    # We've already built the CFG for this function while building the CFG of the
    # enclosing function
    cfg = func_def.cfg

    # Find captured variables
    parent_cfg = bb.cfg
    def_ass_before = set(func_ty.arg_names) | ctx.locals.keys()
    maybe_ass_before = def_ass_before | parent_cfg.maybe_ass_before[bb]
    cfg.analyze(def_ass_before, maybe_ass_before)
    captured = {
        x: ctx.locals[x]
        for x in cfg.live_before[cfg.entry_bb]
        if x not in func_ty.arg_names and x in ctx.locals
    }

    # Captured variables may not be linear
    for v in captured.values():
        if v.ty.linear:
            x = v.name
            using_bb = cfg.live_before[cfg.entry_bb][x]
            raise GuppyError(
                f"Variable `{x}` with linear type `{v.ty}` may not be used here "
                f"because it was defined in an outer scope (at {{0}})",
                using_bb.vars.used[x],
                [v.defined_at],
            )

    # Captured variables may never be assigned to
    for bb in cfg.bbs:
        for v in captured.values():
            x = v.name
            if x in bb.vars.assigned:
                raise GuppyError(
                    f"Variable `{x}` defined in an outer scope (at {{0}}) may not "
                    f"be assigned to",
                    bb.vars.assigned[x],
                    [v.defined_at],
                )

    # Construct inputs for checking the body CFG
    inputs = list(captured.values()) + [
        Variable(x, ty, func_def.args.args[i], None)
        for i, (x, ty) in enumerate(zip(func_ty.arg_names, func_ty.args))
    ]
    globals = ctx.globals

    # Check if the body contains a recursive occurrence of the function name
    if func_def.name in cfg.live_before[cfg.entry_bb]:
        if len(captured) == 0:
            # If there are no captured vars, we treat the function like a global name
            func = DefinedFunction(func_def.name, func_ty, func_def, None)
            globals = ctx.globals | Globals({func_def.name: func}, {})

        else:
            # Otherwise, we treat it like a local name
            inputs.append(Variable(func_def.name, func_def.ty, func_def, None))

    checked_cfg = check_cfg(cfg, inputs, func_ty.returns, globals)
    checked_def = CheckedNestedFunctionDef(
        checked_cfg,
        func_ty,
        captured,
        name=func_def.name,
        args=func_def.args,
        body=func_def.body,
        decorator_list=func_def.decorator_list,
        returns=func_def.returns,
        type_comment=func_def.type_comment,
    )
    return with_loc(func_def, checked_def)


def check_signature(func_def: ast.FunctionDef, globals: Globals) -> FunctionType:
    """Checks the signature of a function definition and returns the corresponding
    Guppy type."""
    if len(func_def.args.posonlyargs) != 0:
        raise GuppyError(
            "Positional-only parameters not supported", func_def.args.posonlyargs[0]
        )
    if len(func_def.args.kwonlyargs) != 0:
        raise GuppyError(
            "Keyword-only parameters not supported", func_def.args.kwonlyargs[0]
        )
    if func_def.args.vararg is not None:
        raise GuppyError("*args not supported", func_def.args.vararg)
    if func_def.args.kwarg is not None:
        raise GuppyError("**kwargs not supported", func_def.args.kwarg)
    if func_def.returns is None:
        # TODO: Error location is incorrect
        if all(r.value is None for r in return_nodes_in_ast(func_def)):
            raise GuppyError(
                "Return type must be annotated. Try adding a `-> None` annotation.",
                func_def,
            )
        raise GuppyError("Return type must be annotated", func_def)

    arg_tys = []
    arg_names = []
    for i, arg in enumerate(func_def.args.args):
        if arg.annotation is None:
            raise GuppyError("Argument type must be annotated", arg)
        ty = type_from_ast(arg.annotation, globals)
        arg_tys.append(ty)
        arg_names.append(arg.arg)

    ret_type = type_from_ast(func_def.returns, globals)
    return FunctionType(arg_tys, ret_type, arg_names)
