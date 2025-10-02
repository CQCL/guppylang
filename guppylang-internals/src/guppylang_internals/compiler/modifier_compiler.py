"""Hugr generation for modifiers."""

from hugr import Wire, ops
from hugr import tys as ht

from guppylang_internals.ast_util import get_type
from guppylang_internals.checker.modifier_checker import non_copyable_front_others_back
from guppylang_internals.compiler.cfg_compiler import compile_cfg
from guppylang_internals.compiler.core import CompilerContext, DFContainer
from guppylang_internals.compiler.expr_compiler import (
    ExprCompiler,
    array_unwrap_elem,
    array_wrap_elem,
)
from guppylang_internals.nodes import CheckedModifiedBlock, PlaceNode
from guppylang_internals.std._internal.compiler.array import (
    array_convert_from_std_array,
    array_convert_to_std_array,
    array_map,
    array_new,
    standard_array_type,
    unpack_array,
)
from guppylang_internals.std._internal.compiler.tket_exts import MODIFIER_EXTENSION
from guppylang_internals.tys.builtin import int_type, is_array_type
from guppylang_internals.tys.ty import InputFlags


def compile_modified_block(
    modified_block: CheckedModifiedBlock,
    dfg: DFContainer,
    ctx: CompilerContext,
    expr_compiler: ExprCompiler,
) -> Wire:
    DAGGER_OP_NAME = "DaggerModifier"
    CONTROL_OP_NAME = "ControlModifier"
    POWER_OP_NAME = "PowerModifier"

    # Define types
    body_ty = modified_block.ty
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
        if InputFlags.Inout not in fn_inp.flags
        and InputFlags.Comptime not in fn_inp.flags
    ]
    in_out_arg = ht.ListArg([t.type_arg() for t in in_out_ht])
    other_in_arg = ht.ListArg([t.type_arg() for t in other_in_ht])

    func_builder = dfg.builder.module_root_builder().define_function(
        str(modified_block), hugr_ty.input, hugr_ty.output
    )

    # compile body
    cfg = compile_cfg(modified_block.cfg, func_builder, func_builder.inputs(), ctx)
    func_builder.set_outputs(*cfg)

    # LoadFunc
    call = dfg.builder.load_function(func_builder, hugr_ty)

    # Function inputs
    captured = [v for v, _ in modified_block.captured.values()]
    captured = non_copyable_front_others_back(captured)
    args = [dfg[v] for v in captured]

    if modified_block.is_dagger():
        dagger_ty = ht.FunctionType([hugr_ty], [hugr_ty])
        call = dfg.builder.add_op(
            ops.ExtOp(
                MODIFIER_EXTENSION.get_op(DAGGER_OP_NAME),
                dagger_ty,
                [in_out_arg, other_in_arg],
            ),
            call,
        )
    qubit_num_args = []
    if modified_block.has_control():
        for control in modified_block.control:
            # definition of types
            assert control.qubit_num is not None
            qubit_num: ht.TypeArg
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
                ht.FunctionType([input_fn_ty], [output_fn_ty]),
            )
            call = dfg.builder.add_op(op, call)
            # update types
            in_out_arg = ht.ListArg([std_array.type_arg(), *in_out_arg.elems])
            hugr_ty = output_fn_ty
    if modified_block.is_power():
        power_ty = ht.FunctionType([hugr_ty, int_type().to_hugr(ctx)], [hugr_ty])
        for power in modified_block.power:
            num = expr_compiler.compile(power.iter, dfg)
            call = dfg.builder.add_op(
                ops.ExtOp(
                    MODIFIER_EXTENSION.get_op(POWER_OP_NAME),
                    power_ty,
                    [in_out_arg, other_in_arg],
                ),
                call,
                num,
            )

    # Prepare control arguments
    ctrl_args: list[Wire] = []
    for i, control in enumerate(modified_block.control):
        if is_array_type(get_type(control.ctrl[0])):
            input_array = expr_compiler.compile(control.ctrl[0], dfg)

            unwrap = array_unwrap_elem(ctx)
            unwrap = dfg.builder.load_function(
                unwrap,
                instantiation=ht.FunctionType([ht.Option(ht.Qubit)], [ht.Qubit]),
                type_args=[ht.TypeTypeArg(ht.Qubit)],
            )
            map_op = array_map(ht.Option(ht.Qubit), qubit_num_args[i], ht.Qubit)
            unwrapped_array = dfg.builder.add_op(map_op, input_array, unwrap)

            unwrapped_array = dfg.builder.add_op(
                array_convert_to_std_array(ht.Qubit, qubit_num_args[i]), unwrapped_array
            )

            ctrl_args.extend(unwrapped_array)
        else:
            cs = [expr_compiler.compile(c, dfg) for c in control.ctrl]
            c_node = dfg.builder.add_op(array_new(ht.Qubit, len(control.ctrl)), *cs)
            val_to_std = array_convert_to_std_array(ht.Qubit, qubit_num_args[i])
            c_node = dfg.builder.add_op(val_to_std, *c_node)
            ctrl_args.append(c_node)

    # Call
    call = dfg.builder.add_op(
        ops.CallIndirect(),
        call,
        *ctrl_args,
        *args,
    )
    outports = iter(call)

    # Unpack controls
    for i, control in enumerate(modified_block.control):
        outport = next(outports)
        if is_array_type(get_type(control.ctrl[0])):
            result_array = dfg.builder.add_op(
                array_convert_from_std_array(ht.Qubit, qubit_num_args[i]), outport
            )

            wrap = array_wrap_elem(ctx)
            wrap = dfg.builder.load_function(
                wrap,
                instantiation=ht.FunctionType([ht.Qubit], [ht.Option(ht.Qubit)]),
                type_args=[ht.TypeTypeArg(ht.Qubit)],
            )
            map_op = array_map(ht.Qubit, qubit_num_args[i], ht.Option(ht.Qubit))
            new_c = dfg.builder.add_op(map_op, result_array, wrap)

            c = control.ctrl[0]
            assert isinstance(c, PlaceNode)

            dfg[c.place] = new_c
        else:
            val_from_std = array_convert_from_std_array(ht.Qubit, qubit_num_args[i])
            std_arr = dfg.builder.add_op(val_from_std, outport)
            unpacked = unpack_array(dfg.builder, std_arr)
            for c, wire in zip(control.ctrl, unpacked, strict=False):
                assert isinstance(c, PlaceNode)
                dfg[c.place] = wire

    for arg in captured:
        if InputFlags.Inout in arg.flags:
            dfg[arg] = next(outports)

    return call
