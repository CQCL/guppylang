from hugr import Wire, ops
from hugr import tys as ht

from guppylang.definition.custom import CustomInoutCallCompiler
from guppylang.definition.value import CallReturnWires
from guppylang.error import InternalGuppyError
from guppylang.nodes import GlobalCall
from guppylang.std._internal.compiler.arithmetic import convert_itousize
from guppylang.std._internal.compiler.prelude import build_unwrap
from guppylang.std._internal.compiler.tket2_exts import (
    FUTURES_EXTENSION,
    WASM_EXTENSION,
    ConstWasmModule,
)
from guppylang.tys.builtin import (
    wasm_module_info,
)
from guppylang.tys.ty import (
    FunctionType,
)


class WasmModuleInitCompiler(CustomInoutCallCompiler):
    """Compiler for initialising WASM modules.
    Calls tket2's "get_context" and unwraps the `Option` result.
    Returns a `tket2.wasm.context` wire.
    """

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        # Make a ConstWasmModule as a CustomConst
        assert len(args) == 1
        ctx_arg = args[0]
        ctx_wire = self.builder.add_op(convert_itousize(), ctx_arg)

        ctx_ty = WASM_EXTENSION.get_type("context").instantiate([])
        get_ctx_op = ops.ExtOp(
            WASM_EXTENSION.get_op("get_context"),
            ht.FunctionType([ht.USize()], [ht.Option(ctx_ty)]),
        )
        node = self.builder.add_op(get_ctx_op, ctx_wire)
        opt_w: Wire = node[0]
        err = "Failed to spawn WASM context"
        out_node = build_unwrap(self.builder, opt_w, err)
        return CallReturnWires(regular_returns=[out_node], inout_returns=[])


class WasmModuleDiscardCompiler(CustomInoutCallCompiler):
    """Compiler for discarding WASM contexts."""

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        assert len(args) == 1
        ctx = args[0]
        op = WASM_EXTENSION.get_op("dispose_context").instantiate([])
        self.builder.add_op(op, ctx)
        return CallReturnWires(regular_returns=[], inout_returns=[])


class WasmModuleCallCompiler(CustomInoutCallCompiler):
    """Compiler for WASM calls
    When a wasm method is called in guppy, we turn it into 2 tket2 ops:
    * lookup: wasm.module -> wasm.func
    * call: wasm.context * wasm.func * inputs -> wasm.context * output

    For the wasm.module that we use in lookup, a constant is created for each
    call, using the wasm file information embedded in method's `self` argument.
    """

    fn_name: str

    def __init__(self, name: str) -> None:
        self.fn_name = name

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        # The arguments should be:
        # - a WASM context
        # - any args meant for the WASM function
        assert len(args) >= 1
        module_ty = WASM_EXTENSION.get_type("module").instantiate([])
        ctx_ty = WASM_EXTENSION.get_type("context").instantiate([])

        fn_name_arg = ht.StringArg(self.fn_name)
        # Function type without Inout context arg (for building)
        assert isinstance(self.node, GlobalCall)
        assert self.func is not None
        wasm_sig = FunctionType(
            self.func.ty.inputs[1:],
            self.func.ty.output,
        ).to_hugr(self.ctx)

        inputs_row_arg = ht.ListArg([ty.type_arg() for ty in wasm_sig.input])
        output_row_arg = ht.ListArg([ty.type_arg() for ty in wasm_sig.output])

        func_ty = WASM_EXTENSION.get_type("func").instantiate(
            [inputs_row_arg, output_row_arg]
        )
        future_ty = FUTURES_EXTENSION.get_type("Future").instantiate(
            [ht.Tuple(*wasm_sig.output).type_arg()]
        )

        # Get the WASM module information from the type
        selfarg = self.func.ty.inputs[0].ty
        if info := wasm_module_info(selfarg):
            const_module = self.builder.add_const(ConstWasmModule(*info))
        else:
            raise InternalGuppyError(
                "Expected cached signature to have WASM module as first arg"
            )

        wasm_module = self.builder.load(const_module)

        # Lookup the function we want
        wasm_opdef = WASM_EXTENSION.get_op("lookup").instantiate(
            [fn_name_arg, inputs_row_arg, output_row_arg],
            ht.FunctionType([module_ty], [func_ty]),
        )
        wasm_func = self.builder.add_op(wasm_opdef, wasm_module)

        # Call the function
        call_op = WASM_EXTENSION.get_op("call").instantiate(
            [inputs_row_arg, output_row_arg],
            ht.FunctionType([ctx_ty, func_ty, *wasm_sig.input], [ctx_ty, future_ty]),
        )

        ctx, future = self.builder.add_op(call_op, args[0], wasm_func, *args[1:])

        read_opdef = FUTURES_EXTENSION.get_op("Read").instantiate(
            [ht.Tuple(*wasm_sig.output).type_arg()],
            ht.FunctionType([future_ty], [ht.Tuple(*wasm_sig.output)]),
        )
        result = self.builder.add_op(read_opdef, future)
        ws: list[Wire] = list(result[:])
        node = self.builder.add_op(ops.UnpackTuple(wasm_sig.output), *ws)
        ws: list[Wire] = list(node[:])

        return CallReturnWires(regular_returns=ws, inout_returns=[ctx])
