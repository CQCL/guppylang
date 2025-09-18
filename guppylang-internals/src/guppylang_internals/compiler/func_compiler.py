from typing import TYPE_CHECKING

from guppylang_internals.ast_util import get_type
from guppylang_internals.checker.func_checker import linear_front_others_back
from guppylang_internals.checker.stmt_checker import qubit_ty
from guppylang_internals.compiler.expr_compiler import ExprCompiler, array_unwrap_elem, array_wrap_elem
from guppylang_internals.std._internal.compiler.array import array_convert_from_std_array, array_convert_to_std_array, array_map, array_new, standard_array_type, unpack_array
from guppylang_internals.std._internal.compiler.tmp_modifier_exts import MODIFIER_EXTENSION
from guppylang_internals.tys.builtin import array_type, int_type, is_array_type
from guppylang_internals.tys.ty import InputFlags
from hugr import Wire, ops
from hugr import tys as ht
import hugr
from hugr.build.function import Function

from guppylang_internals.compiler.cfg_compiler import compile_cfg
from guppylang_internals.compiler.core import CompilerContext, DFContainer
from guppylang_internals.compiler.hugr_extension import PartialOp
from guppylang_internals.nodes import CheckedModifier, CheckedNestedFunctionDef, PlaceNode

if TYPE_CHECKING:
    from guppylang_internals.definition.function import CheckedFunctionDef


def compile_global_func_def(
    func: "CheckedFunctionDef",
    builder: Function,
    ctx: CompilerContext,
) -> None:
    """Compiles a top-level function definition to Hugr."""
    cfg = compile_cfg(func.cfg, builder, builder.inputs(), ctx)
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
    closure_ty = ht.FunctionType(
        [*captured_types, *func_ty.input], func_ty.output)
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


# TODO: (k.hirata) WIP
def compile_modifier(
    modifier: CheckedModifier,
    dfg: DFContainer,
    ctx: CompilerContext,
    expr_compiler: ExprCompiler,
) -> Wire:
    DAGGER_OP_NAME = "DaggerModifier"
    CONTROL_OP_NAME = "ControlModifier"
    POWER_OP_NAME = "PowerModifier"

    # Define types
    body_ty = modifier.ty
    # TODO: Shouldn't this be `to_hugr_poly`?
    hugr_ty = body_ty.to_hugr(ctx)
    in_out_ht = [
        fn_inp.ty.to_hugr(ctx)
        for fn_inp in body_ty.inputs
        if InputFlags.Inout in fn_inp.flags and InputFlags.Comptime not in fn_inp.flags
    ]
    other_in_ht = [
        fn_inp.ty.to_hugr(ctx)
        for fn_inp in body_ty.inputs
        if InputFlags.Inout not in fn_inp.flags and InputFlags.Comptime not in fn_inp.flags
    ]
    in_out_arg = ht.ListArg([t.type_arg() for t in in_out_ht])
    other_in_arg = ht.ListArg([t.type_arg() for t in other_in_ht])

    # Body of modifier to a function
    from guppylang_internals.definition.function import CompiledFunctionDef
    func_builder = dfg.builder.module_root_builder().define_function(
        str(modifier), hugr_ty.input, hugr_ty.output
    )
    mono_args = ()
    ctx.compiled[modifier.def_id, mono_args] = CompiledFunctionDef(
        modifier.def_id,
        str(modifier),
        modifier,
        mono_args,
        body_ty,
        None,
        modifier.cfg,
        func_builder,
    )
    ctx.worklist[modifier.def_id, mono_args] = None

    # LoadFunc
    call = dfg.builder.load_function(func_builder, hugr_ty)

    # Function inputs
    captured = [v for v, _ in modifier.captured.values()]
    captured = linear_front_others_back(captured)
    args = [dfg[v] for v in captured]

    if modifier.is_dagger():
        dagger_ty = ht.FunctionType([hugr_ty], [hugr_ty])
        call = dfg.builder.add_op(
            ops.ExtOp(MODIFIER_EXTENSION.get_op(DAGGER_OP_NAME),
                      dagger_ty, [in_out_arg, other_in_arg]),
            call,
        )
    qubit_num_args = []
    if modifier.has_control():
        for control in modifier.control:
            # definition of types
            assert control.qubit_num is not None
            if isinstance(control.qubit_num, int):
                qubit_num = ht.BoundedNatArg(control.qubit_num)
            else:
                qubit_num = control.qubit_num.to_arg().to_hugr(ctx)
            qubit_num_args.append(qubit_num)
            std_array = standard_array_type(ht.Qubit, qubit_num)

            # control operator
            input_fn_ty = hugr_ty
            output_fn_ty = ht.FunctionType(
                [std_array, *hugr_ty.input], [std_array, *hugr_ty.output]
            )
            op = MODIFIER_EXTENSION.get_op(CONTROL_OP_NAME).instantiate(
                [qubit_num, in_out_arg, other_in_arg],
                ht.FunctionType([input_fn_ty], [output_fn_ty])
            )
            call = dfg.builder.add_op(op, call)
            # update types
            in_out_arg = ht.ListArg([std_array.type_arg(), *in_out_arg.elems])
            hugr_ty = output_fn_ty
    if modifier.is_power():
        # TODO (k.hirata): hugr signature is wrong. It does not take an integer argument.
        power_ty = ht.FunctionType([hugr_ty, int_type().to_hugr(ctx)], [hugr_ty])
        for power in modifier.power:
            num = expr_compiler.compile(power.iter, dfg)
            call = dfg.builder.add_op(
                ops.ExtOp(MODIFIER_EXTENSION.get_op(POWER_OP_NAME),
                          power_ty, [in_out_arg, other_in_arg]),
                call, num
            )

    # Prepare control arguments
    ctrl_args = []
    for i, control in enumerate(modifier.control):
        if is_array_type(get_type(control.ctrl[0])):
            input_array = expr_compiler.compile(control.ctrl[0], dfg)

            unwrap = array_unwrap_elem(ctx)
            unwrap = dfg.builder.load_function(
                unwrap,
                instantiation=ht.FunctionType([ht.Option(ht.Qubit)], [ht.Qubit]),
                type_args=[ht.TypeTypeArg(ht.Qubit)]
            )
            map_op = array_map(ht.Option(ht.Qubit), qubit_num_args[i], ht.Qubit)
            unwrapped_array = dfg.builder.add_op(map_op, input_array, unwrap)

            unwrapped_array = dfg.builder.add_op(
                array_convert_to_std_array(ht.Qubit, qubit_num_args[i]), unwrapped_array
            )

            ctrl_args.extend(unwrapped_array)
        else:
            cs = [expr_compiler.compile(c, dfg) for c in control.ctrl]
            c = dfg.builder.add_op(
                array_new(ht.Qubit, len(control.ctrl)), *cs
            )
            val_to_std = array_convert_to_std_array(ht.Qubit, qubit_num_args[i])
            c = dfg.builder.add_op(val_to_std, *c)
            ctrl_args.append(c)

    # Call
    call = dfg.builder.add_op(
        ops.CallIndirect(),
        call,
        *ctrl_args, *args,
    )
    wires = iter(call)

    # Unpack controls
    for i, control in enumerate(modifier.control):
        wire = next(wires)
        if is_array_type(get_type(control.ctrl[0])):
            result_array = dfg.builder.add_op(
                array_convert_from_std_array(ht.Qubit, qubit_num_args[i]),  wire
            )

            wrap = array_wrap_elem(ctx)
            wrap = dfg.builder.load_function(
                wrap,
                instantiation=ht.FunctionType([ht.Qubit], [ht.Option(ht.Qubit)]),
                type_args=[ht.TypeTypeArg(ht.Qubit)]
            )
            map_op = array_map(ht.Qubit, qubit_num_args[i], ht.Option(ht.Qubit))
            wire = dfg.builder.add_op(map_op, result_array, wrap)

            c = control.ctrl[0]
            assert isinstance(c, PlaceNode)

            dfg[c.place] = wire
        else:
            val_from_std = array_convert_from_std_array(ht.Qubit, qubit_num_args[i])
            wire = dfg.builder.add_op(val_from_std, wire)
            unpacked = unpack_array(dfg.builder, wire)
            for c, wire in zip(control.ctrl, unpacked):
                assert isinstance(c, PlaceNode)
                dfg[c.place] = wire

    for arg in captured:
        if InputFlags.Inout in arg.flags:
            dfg[arg] = next(wires)

    return call
