"""Type checking code for top-level and nested function definitions.

For top-level functions, we take the `DefinedFunction` containing the `ast.FunctionDef`
node straight from the Python AST. We build a CFG, check it, and return a
`CheckedFunction` containing a `CheckedCFG` with type annotations.
"""

import ast
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from guppylang.ast_util import return_nodes_in_ast, with_loc
from guppylang.cfg.bb import BB
from guppylang.cfg.builder import CFGBuilder
from guppylang.checker.cfg_checker import CheckedCFG, check_cfg
from guppylang.checker.core import Context, Globals, Place, Variable
from guppylang.checker.errors.generic import UnsupportedError
from guppylang.definition.common import DefId
from guppylang.diagnostic import Error, Help, Note
from guppylang.error import GuppyError
from guppylang.nodes import CheckedNestedFunctionDef, NestedFunctionDef
from guppylang.tys.parsing import parse_function_io_types
from guppylang.tys.ty import FunctionType, InputFlags, NoneType

if TYPE_CHECKING:
    from guppylang.tys.param import Parameter


@dataclass(frozen=True)
class IllegalAssignError(Error):
    title: ClassVar[str] = "Illegal assignment"
    span_label: ClassVar[str] = (
        "Variable `{var}` may not be assigned to since `{var}` is captured from an "
        "outer scope"
    )
    var: str

    @dataclass(frozen=True)
    class DefHint(Note):
        span_label: ClassVar[str] = "`{var}` defined here"
        var: str


@dataclass(frozen=True)
class MissingArgAnnotationError(Error):
    title: ClassVar[str] = "Missing type annotation"
    span_label: ClassVar[str] = "Argument requires a type annotation"


@dataclass(frozen=True)
class MissingReturnAnnotationError(Error):
    title: ClassVar[str] = "Missing type annotation"
    span_label: ClassVar[str] = "Return type must be annotated"

    @dataclass(frozen=True)
    class ReturnNone(Help):
        message: ClassVar[str] = (
            "Looks like `{func}` doesn't return anything. Consider annotating it with "
            "`-> None`."
        )
        func: str


def check_global_func_def(
    func_def: ast.FunctionDef, ty: FunctionType, globals: Globals
) -> CheckedCFG[Place]:
    """Type checks a top-level function definition."""
    args = func_def.args.args
    returns_none = isinstance(ty.output, NoneType)
    assert ty.input_names is not None

    cfg = CFGBuilder().build(func_def.body, returns_none, globals)
    inputs = [
        Variable(x, inp.ty, loc, inp.flags)
        for x, inp, loc in zip(ty.input_names, ty.inputs, args, strict=True)
    ]
    generic_params = {
        param.name: param.with_idx(i) for i, param in enumerate(ty.params)
    }
    return check_cfg(cfg, inputs, ty.output, generic_params, func_def.name, globals)


def check_nested_func_def(
    func_def: NestedFunctionDef, bb: BB, ctx: Context
) -> CheckedNestedFunctionDef:
    """Type checks a local (nested) function definition."""
    func_ty = check_signature(func_def, ctx.globals)
    assert func_ty.input_names is not None

    if func_ty.parametrized:
        raise GuppyError(
            UnsupportedError(func_def, "Nested generic function definitions")
        )

    # We've already built the CFG for this function while building the CFG of the
    # enclosing function
    cfg = func_def.cfg

    # Find captured variables
    parent_cfg = bb.containing_cfg
    def_ass_before = set(func_ty.input_names) | ctx.locals.keys()
    maybe_ass_before = def_ass_before | parent_cfg.maybe_ass_before[bb]
    inout_vars = inout_var_names(func_ty)
    cfg.analyze(def_ass_before, maybe_ass_before, inout_vars)
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
                err = IllegalAssignError(bb.vars.assigned[x], x)
                err.add_sub_diagnostic(IllegalAssignError.DefHint(v.defined_at, x))
                raise GuppyError(err)

    # Construct inputs for checking the body CFG
    inputs = [v for v, _ in captured.values()] + [
        Variable(x, inp.ty, func_def.args.args[i], inp.flags)
        for i, (x, inp) in enumerate(
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

    checked_cfg = check_cfg(cfg, inputs, func_ty.output, {}, func_def.name, globals)
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
            UnsupportedError(func_def.args.posonlyargs[0], "Positional-only parameters")
        )
    if len(func_def.args.kwonlyargs) != 0:
        raise GuppyError(
            UnsupportedError(func_def.args.kwonlyargs[0], "Keyword-only parameters")
        )
    if func_def.args.vararg is not None:
        raise GuppyError(UnsupportedError(func_def.args.vararg, "Variadic args"))
    if func_def.args.kwarg is not None:
        raise GuppyError(UnsupportedError(func_def.args.kwarg, "Keyword args"))
    if func_def.args.defaults:
        raise GuppyError(
            UnsupportedError(func_def.args.defaults[0], "Default arguments")
        )
    if func_def.returns is None:
        err = MissingReturnAnnotationError(func_def)
        # TODO: Error location is incorrect
        if all(r.value is None for r in return_nodes_in_ast(func_def)):
            err.add_sub_diagnostic(
                MissingReturnAnnotationError.ReturnNone(None, func_def.name)
            )
        raise GuppyError(err)

    # TODO: Prepopulate mapping when using Python 3.12 style generic functions
    param_var_mapping: dict[str, Parameter] = {}
    input_nodes = []
    input_names = []
    for inp in func_def.args.args:
        ty_ast = inp.annotation
        if ty_ast is None:
            raise GuppyError(MissingArgAnnotationError(inp))
        input_nodes.append(ty_ast)
        input_names.append(inp.arg)
    inputs, output = parse_function_io_types(
        input_nodes, func_def.returns, func_def, globals, param_var_mapping, True
    )
    return FunctionType(
        inputs,
        output,
        input_names,
        sorted(param_var_mapping.values(), key=lambda v: v.idx),
    )


def parse_function_with_docstring(
    func_ast: ast.FunctionDef,
) -> tuple[ast.FunctionDef, str | None]:
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


def inout_var_names(func_ty: FunctionType) -> list[str]:
    """Returns the names of all borrowed arguments in a function type."""
    assert func_ty.input_names is not None
    return [
        x
        for inp, x in zip(func_ty.inputs, func_ty.input_names, strict=True)
        if InputFlags.Inout in inp.flags
    ]
