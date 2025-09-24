"""Type checking code for modifiers.
"""

import ast
from guppylang_internals.ast_util import loop_in_ast, with_loc
from guppylang_internals.cfg.bb import BB
from guppylang_internals.checker.cfg_checker import check_cfg
from guppylang_internals.checker.core import Context, Variable
from guppylang_internals.checker.errors.generic import AssignUnderDagger, LoopUnderDagger
from guppylang_internals.definition.common import DefId
from guppylang_internals.error import GuppyError
from guppylang_internals.nodes import CheckedModifier, Modifier
from guppylang_internals.tys.ty import FuncInput, FunctionType, InputFlags, NoneType, Type


def check_modifier(
    modifier: Modifier, bb: BB, ctx: Context
) -> CheckedModifier:
    """Type checks a modifier definition."""
    cfg = modifier.cfg

    # Find captured variables
    parent_cfg = bb.containing_cfg
    def_ass_before = ctx.locals.keys()
    maybe_ass_before = def_ass_before | parent_cfg.maybe_ass_before[bb]

    cfg.analyze(def_ass_before, maybe_ass_before, [])
    captured = {
        x: (_set_inout_if_linear(ctx.locals[x]), using_bb.vars.used[x])
        for x, using_bb in cfg.live_before[cfg.entry_bb].items()
        if x in ctx.locals
    }

    # We do not allow any assignments if it is daggered.
    if modifier.is_dagger():
        for stmt in modifier.body:
            loops = loop_in_ast(stmt)
            if len(loops) != 0:
                loop = next(iter(loops))
                err = LoopUnderDagger(loop)
                err.add_sub_diagnostic(LoopUnderDagger.Dagger(modifier.span_ctxt_manager()))
                raise GuppyError(err)

        for cfg_bb in cfg.bbs:
            if cfg_bb.vars.assigned:
                _, v = next(iter(cfg_bb.vars.assigned.items()))
                err = AssignUnderDagger(v)
                err.add_sub_diagnostic(AssignUnderDagger.Modifier(modifier.span_ctxt_manager()))
                raise GuppyError(err)


        # TODO (k.hirata): check all the calls
    
    if modifier.is_control():
        # TODO (k.hirata): check all the calls
        pass
    
    if modifier.is_power():
        # Do we need to check anything here?
        pass

    # Construct inputs for checking the body CFG
    inputs = [v for v, _ in captured.values()]
    inputs = linear_front_others_back(inputs)
    def_id = DefId.fresh()
    globals = ctx.globals

    # TODO: (k.hirata) Ad hoc name for new function
    # This name is printed, for example, when the linearity checker fails in the modifier body
    checked_cfg = check_cfg(cfg, inputs, NoneType(), {}, "__modified__()", globals)
    func_ty = check_modifier_signature(checked_cfg.input_tys)

    checked_modifier = CheckedModifier(
        def_id,
        checked_cfg,
        func_ty,
        captured,
        modifier.dagger,
        modifier.control,
        modifier.power,
        **dict(ast.iter_fields(modifier)),
    )
    return with_loc(modifier, checked_modifier)


def _set_inout_if_linear(
    var: Variable
) -> Variable:
    """Set the `inout` flag if the variable is linear."""
    if var.ty.linear:
        return var.add_flags(InputFlags.Inout)
    else:
        return var


def check_modifier_signature(
    input_tys: list[Type]
) -> FunctionType:
    """Check and create the signature of a function definition for a body of a `With` block."""
    # TODO: It could be inout or owned
    func_ty = FunctionType(
        [FuncInput(t, InputFlags.Inout if t.linear else InputFlags.NoFlags) for t in input_tys],
        NoneType(),
    )
    return func_ty

def linear_front_others_back(v: list[Variable]) -> list[Variable]:
    """Reorder variables so that linear ones come first, preserving the relative order
    of linear and non-linear variables."""
    linear_vars = [x for x in v if x.ty.linear]
    non_linear_vars = [x for x in v if not x.ty.linear]
    return linear_vars + non_linear_vars