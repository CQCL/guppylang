from typing import TYPE_CHECKING

from guppylang_internals.compiler.expr_compiler import ExprCompiler
from guppylang_internals.std._internal.compiler.tmp_modifier_exts import MODIFIER_EXTENSION
from guppylang_internals.tys.ty import InputFlags
from hugr import Wire, ops
from hugr import tys as ht
from hugr.build.function import Function

from guppylang_internals.compiler.cfg_compiler import compile_cfg
from guppylang_internals.compiler.core import CompilerContext, DFContainer
from guppylang_internals.compiler.hugr_extension import PartialOp
from guppylang_internals.nodes import CheckedModifier, CheckedNestedFunctionDef, LocalCall

if TYPE_CHECKING:
    from guppylang_internals.definition.function import CheckedFunctionDef


def compile_global_func_def(
    func: "CheckedFunctionDef",
    builder: Function,
    ctx: CompilerContext,
) -> None:
    """Compiles a top-level function definition to Hugr."""
    cfg = compile_cfg(func.cfg, builder, builder.inputs(), ctx)
    print("  compile_global_func_def: setting outputs for", func.name)
    builder.set_outputs(*cfg)


def compile_local_func_def(
    func: CheckedNestedFunctionDef,
    dfg: DFContainer,
    ctx: CompilerContext,
) -> Wire:
    """Compiles a local (nested) function definition to Hugr and loads it into a value.

    Returns the wire output of the `LoadFunc` operation.
    """
    assert func.ty.input_names is not None

    # Pick an order for the captured variables
    captured = list(func.captured.values())
    captured_types = [v.ty.to_hugr(ctx) for v, _ in captured]

    # Whether the function calls itself recursively.
    recursive = func.name in func.cfg.live_before[func.cfg.entry_bb]

    # Prepend captured variables to the function arguments
    func_ty = func.ty.to_hugr(ctx)
    closure_ty = ht.FunctionType([*captured_types, *func_ty.input], func_ty.output)
    func_builder = dfg.builder.module_root_builder().define_function(
        func.name, closure_ty.input, closure_ty.output
    )

    # Nested functions are not generic, so no need to worry about monomorphization
    mono_args = ()

    # If we have captured variables and the body contains a recursive occurrence of
    # the function itself, then we provide the partially applied function as a local
    # variable
    call_args: list[Wire] = list(func_builder.inputs())
    if len(captured) > 0 and recursive:
        loaded = func_builder.load_function(func_builder, closure_ty)
        partial = func_builder.add_op(
            PartialOp.from_closure(closure_ty, captured_types),
            loaded,
            *func_builder.input_node[: len(captured)],
        )

        call_args.append(partial)
        func.cfg.input_tys.append(func.ty)

        # Compile the CFG
        cfg = compile_cfg(func.cfg, func_builder, call_args, ctx)
        func_builder.set_outputs(*cfg)
    else:
        # Otherwise, we treat the function like a normal global variable
        from guppylang_internals.definition.function import CompiledFunctionDef

        ctx.compiled[func.def_id, mono_args] = CompiledFunctionDef(
            func.def_id,
            func.name,
            func,
            mono_args,
            func.ty,
            None,
            func.cfg,
            func_builder,
        )
        # will compile the CFG later
        ctx.worklist[func.def_id, mono_args] = None

    # Finally, load the function into the local data-flow graph
    loaded = dfg.builder.load_function(func_builder, closure_ty)
    if len(captured) > 0:
        loaded = dfg.builder.add_op(
            PartialOp.from_closure(closure_ty, captured_types),
            loaded,
            *(dfg[v] for v, _ in captured),
        )

    return loaded

DAGGER_OP_NAME = "DaggerModifier"
CONTROL_OP_NAME = "ControlModifier"
POWER_OP_NAME = "PowerModifier"

# TODO: (k.hirata) WIP
def compile_modifier(
    modifier: CheckedModifier,
    dfg: DFContainer,
    ctx: CompilerContext,
    expr_compiler: ExprCompiler,
) -> Wire:
    print("  modifier.ty @ compile_modifier = ", modifier.ty)
    func_ty = modifier.ty.to_hugr(ctx)
    print("  func_ty @ compile_modifier = ", func_ty)
    closure_ty = ht.FunctionType(
        [*func_ty.input], func_ty.output)
    func_builder = dfg.builder.module_root_builder().define_function(
        str(modifier), closure_ty.input, closure_ty.output
    )

    # We treat the function like a normal global variable
    from guppylang_internals.definition.function import CompiledFunctionDef
    mono_args = ()

    print("  modifier.ty @ compile_modifier = ", modifier.ty)
    ctx.compiled[modifier.def_id, mono_args] = CompiledFunctionDef(
        modifier.def_id,
        str(modifier),
        modifier,
        mono_args,
        modifier.ty,
        None,
        modifier.cfg,
        func_builder,
    )
    ctx.worklist[modifier.def_id, mono_args] = None  # will compile the CFG later
    print("  adding None to worklist with index [modifier.def_id] = ", modifier.def_id )

    call = dfg.builder.load_function(func_builder, closure_ty)

    captured = [v for v, _ in modifier.captured.values()]
    args = [dfg[v] for v in captured]

    ## TODO (k.hirata): ExtensionOp such as `ControlModifier` or `DaggerModifier` need to be inserted here
    input_ty = ht.ListArg([t.type_arg() for t in func_ty.input])
    output_ty = ht.ListArg([t.type_arg() for t in func_ty.output])

    # WIP
    if modifier.is_dagger():
        dagger_ty = ht.FunctionType([func_ty], [func_ty])
        tmp_emp_arg = ht.ListArg([])
        call = dfg.builder.add_op(
            ops.ExtOp(MODIFIER_EXTENSION.get_op(DAGGER_OP_NAME), dagger_ty, [input_ty, tmp_emp_arg]),
            call,
        )
    if modifier.is_power():
        power_ty = ht.FunctionType([func_ty], [func_ty])
        tmp_emp_arg = ht.ListArg([])
        call = dfg.builder.add_op(
            ops.ExtOp(MODIFIER_EXTENSION.get_op(POWER_OP_NAME), power_ty, [input_ty, tmp_emp_arg]),
            call,
        )
    if modifier.has_control():
        # TODO: Make a big array to flatten control arguments.
        control_ty = ht.FunctionType([func_ty], [func_ty])
        # Placeholder
        length = ht.BoundedNatArg(100)
        tmp_emp_arg = ht.ListArg([])
        call = dfg.builder.add_op(
            ops.ExtOp(MODIFIER_EXTENSION.get_op(CONTROL_OP_NAME), control_ty, [length, input_ty, tmp_emp_arg]),
            call,
        )

    call = dfg.builder.add_op(
        ops.CallIndirect(closure_ty),
        call,
        *args,
    )
    print("[CheckPoint]: CallIndirect operation created with ...")
    wires = iter(call)
    for arg in captured:
        if InputFlags.Inout in arg.flags:
            dfg[arg] = next(wires)

    return call
