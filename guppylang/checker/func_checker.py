"""Type checking code for top-level and nested function definitions.

For top-level functions, we take the `DefinedFunction` containing the `ast.FunctionDef`
node straight from the Python AST. We build a CFG, check it, and return a
`CheckedFunction` containing a `CheckedCFG` with type annotations.
"""

import ast
from typing import TYPE_CHECKING

from guppylang.ast_util import return_nodes_in_ast, with_loc
from guppylang.cfg.bb import BB
from guppylang.cfg.builder import CFGBuilder
from guppylang.checker.cfg_checker import CheckedCFG, check_cfg
from guppylang.checker.core import Context, Globals, Variable
from guppylang.definition.common import DefId
from guppylang.error import GuppyError
from guppylang.nodes import CheckedNestedFunctionDef, NestedFunctionDef
from guppylang.tys.parsing import type_from_ast
from guppylang.tys.ty import FunctionType, NoneType

if TYPE_CHECKING:
    from guppylang.tys.param import Parameter


def check_global_func_def(
    func_def: ast.FunctionDef, ty: FunctionType, globals: Globals
) -> CheckedCFG:
    """Type checks a top-level function definition."""
    args = func_def.args.args
    returns_none = isinstance(ty.output, NoneType)
    assert ty.input_names is not None

    cfg = CFGBuilder().build(func_def.body, returns_none, globals)
    inputs = [
        Variable(x, ty, loc)
        for x, ty, loc in zip(ty.input_names, ty.inputs, args, strict=True)
    ]
    return check_cfg(cfg, inputs, ty.output, globals)


def check_nested_func_def(
    func_def: NestedFunctionDef, bb: BB, ctx: Context
) -> CheckedNestedFunctionDef:
    """Type checks a local (nested) function definition."""
    func_ty = check_signature(func_def, ctx.globals)
    assert func_ty.input_names is not None

    # We've already built the CFG for this function while building the CFG of the
    # enclosing function
    cfg = func_def.cfg

    # Find captured variables
    parent_cfg = bb.containing_cfg
    def_ass_before = set(func_ty.input_names) | ctx.locals.keys()
    maybe_ass_before = def_ass_before | parent_cfg.maybe_ass_before[bb]
    cfg.analyze(def_ass_before, maybe_ass_before)
    captured = {
        x: (ctx.locals[x], using_bb.vars.used[x])
        for x, using_bb in cfg.live_before[cfg.entry_bb].items()
        if x not in func_ty.input_names and x in ctx.locals
    }

    # Captured variables may never be assigned to
    for bb in cfg.bbs:
        for v, _ in captured.values():
            x = v.name
            if x in bb.vars.assigned:
                raise GuppyError(
                    f"Variable `{x}` defined in an outer scope (at {{0}}) may not "
                    f"be assigned to",
                    bb.vars.assigned[x],
                    [v.defined_at],
                )

    # Construct inputs for checking the body CFG
    inputs = [v for v, _ in captured.values()] + [
        Variable(x, ty, func_def.args.args[i])
        for i, (x, ty) in enumerate(
            zip(func_ty.input_names, func_ty.inputs, strict=True)
        )
    ]
    def_id = DefId.fresh()
    globals = ctx.globals

    # Check if the body contains a free (recursive) occurrence of the function name.
    # By checking if the name is free at the entry BB, we avoid false positives when
    # a user shadows the name with a local variable
    if func_def.name in cfg.live_before[cfg.entry_bb]:
        if not captured:
            # If there are no captured vars, we treat the function like a global name
            from guppylang.definition.function import ParsedFunctionDef

            func = ParsedFunctionDef(
                def_id, func_def.name, func_def, func_ty, globals.python_scope, None
            )
            globals = ctx.globals | Globals(
                {func.id: func}, {func_def.name: func.id}, {}, {}
            )
        else:
            # Otherwise, we treat it like a local name
            inputs.append(Variable(func_def.name, func_def.ty, func_def))

    checked_cfg = check_cfg(cfg, inputs, func_ty.output, globals)
    checked_def = CheckedNestedFunctionDef(
        def_id,
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

    # TODO: Prepopulate mapping when using Python 3.12 style generic functions
    param_var_mapping: dict[str, Parameter] = {}
    input_tys = []
    input_names = []
    for inp in func_def.args.args:
        if inp.annotation is None:
            raise GuppyError("Argument type must be annotated", inp)
        ty = type_from_ast(inp.annotation, globals, param_var_mapping)
        input_tys.append(ty)
        input_names.append(inp.arg)
    ret_type = type_from_ast(func_def.returns, globals, param_var_mapping)

    return FunctionType(
        input_tys,
        ret_type,
        input_names,
        sorted(param_var_mapping.values(), key=lambda v: v.idx),
    )


def parse_docstring(func_ast: ast.FunctionDef) -> tuple[ast.FunctionDef, str | None]:
    """Check if the first line of a function is a docstring.

    If it is, return the function with the docstring removed, plus the docstring.
    Else, return the original function and `None`
    """
    docstring = None
    match func_ast.body:
        case [doc, *xs]:
            if (
                isinstance(doc, ast.Expr)
                and isinstance(doc.value, ast.Constant)
                and isinstance(doc.value.value, str)
            ):
                docstring = doc.value.value
                func_ast.body = xs
        case _:
            pass
    return func_ast, docstring
