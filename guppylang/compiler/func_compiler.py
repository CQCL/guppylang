from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

from hugr import Wire, ops
from hugr import tys as ht
from hugr.function import Function

from guppylang.compiler.cfg_compiler import compile_cfg
from guppylang.compiler.core import CompiledGlobals, DFContainer
from guppylang.nodes import CheckedNestedFunctionDef
from guppylang.tys.ty import FunctionType, Type

if TYPE_CHECKING:
    from guppylang.definition.function import CheckedFunctionDef


def compile_global_func_def(
    func: "CheckedFunctionDef",
    builder: Function,
    globals: CompiledGlobals,
) -> None:
    """Compiles a top-level function definition to Hugr."""
    cfg = compile_cfg(func.cfg, builder, builder.inputs(), globals)

    builder.set_outputs(*cfg)


def compile_local_func_def(
    func: CheckedNestedFunctionDef,
    dfg: DFContainer,
    globals: CompiledGlobals,
) -> tuple[Function, Wire]:
    """Compiles a local (nested) function definition to Hugr and loads it into a value.

    Returns the compiled function node, and the wire output of the `LoadFunc` operation.
    """
    assert func.ty.input_names is not None

    # Pick an order for the captured variables
    captured = list(func.captured.values())
    captured_types = [v.ty for v, _ in captured]

    # Whether the function calls itself recursively.
    recursive = func.name in func.cfg.live_before[func.cfg.entry_bb]

    # Prepend captured variables to the function arguments
    closure_ty = FunctionType(
        captured_types + list(func.ty.inputs),
        func.ty.output,
        input_names=[v.name for v, _ in captured] + list(func.ty.input_names),
    )
    hugr_closure_ty: ht.FunctionType = closure_ty.to_hugr_poly().body

    func_builder = dfg.builder.define_function(
        func.name, hugr_closure_ty.input, hugr_closure_ty.output
    )

    # If we have captured variables and the body contains a recursive occurrence of
    # the function itself, then we provide the partially applied function as a local
    # variable
    call_args = cast(list[Wire], func_builder.inputs())
    if len(captured) > 0 and recursive:
        loaded = func_builder.load_function(func_builder, hugr_closure_ty)
        partial = func_builder.add_op(
            make_partial_op(closure_ty, captured_types),
            loaded,
            *func_builder.input_node[: len(captured)],
        )

        call_args.append(partial)
        func.cfg.input_tys.append(func.ty)
    else:
        # Otherwise, we treat the function like a normal global variable
        from guppylang.definition.function import CompiledFunctionDef

        globals = globals | {
            func.def_id: CompiledFunctionDef(
                func.def_id,
                func.name,
                func,
                func.ty,
                {},
                None,
                func.cfg,
                func_builder,
            )
        }

    # Compile the CFG
    cfg = compile_cfg(func.cfg, func_builder, call_args, globals)
    func_builder.set_outputs(*cfg)

    # Finally, load the function into the local data-flow graph
    loaded = dfg.builder.load_function(func_builder, hugr_closure_ty)
    if len(captured) > 0:
        loaded = dfg.builder.add_op(
            make_partial_op(closure_ty, captured_types),
            loaded,
            *(dfg[v] for v, _ in captured),
        )

    return (func_builder, loaded)


def make_dummy_op(
    name: str, inp: Sequence[Type], out: Sequence[Type], extension: str = "dummy"
) -> ops.DataflowOp:
    """Dummy operation."""
    input = [ty.to_hugr() for ty in inp]
    output = [ty.to_hugr() for ty in out]

    sig = ht.FunctionType(input=input, output=output)
    return ops.Custom(name=name, extension=extension, signature=sig, args=[])


def make_partial_op(
    closure_ty: FunctionType, captured_tys: Sequence[Type]
) -> ops.DataflowOp:
    """Creates a dummy operation for partially evaluating a function.

    args:
        closure_ty: A function type `a_0, ..., a_n -> b_0, ..., b_m`
        captured_tys: A list of types `c_0, ..., c_k` that are captured by the function

    returns:
        An operation with type
            ` ( a_0, ..., a_n, c_0, ..., c_k -> b_0, ..., b_m )`
            `-> a_0, ..., a_n -> b_0, ..., b_m`
    """
    all_inputs = closure_ty.inputs + captured_tys
    full_func_ty = FunctionType(all_inputs, closure_ty.output)

    assert len(closure_ty.inputs) >= len(captured_tys)
    assert [p.to_hugr() for p in captured_tys] == [
        ty.to_hugr() for ty in closure_ty.inputs[: len(captured_tys)]
    ]
    return make_dummy_op(
        "partial",
        [full_func_ty, *captured_tys],
        [closure_ty],
        extension="guppylang.unsupported",
    )
