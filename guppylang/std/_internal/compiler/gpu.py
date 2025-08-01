from hugr import Wire, ops
from hugr import tys as ht

from guppylang.definition.custom import CustomInoutCallCompiler
from guppylang.definition.value import CallReturnWires
from guppylang.error import InternalGuppyError
from guppylang.nodes import GlobalCall
from guppylang.std._internal.compiler.arithmetic import convert_itousize
from guppylang.std._internal.compiler.prelude import build_unwrap
from guppylang.std._internal.compiler.tket_exts import (
    FUTURES_EXTENSION,
    GPU_EXTENSION,
    ConstGpuModule,
)
from guppylang.tys.builtin import (
    gpu_module_info,
)
from guppylang.tys.ty import (
    FunctionType,
)


class GpuModuleInitCompiler(CustomInoutCallCompiler):
    """Compiler for initialising GPU modules.
    Calls tket2's "get_context" and unwraps the `Option` result.
    Returns a `tket2.gpu.context` wire.
    """

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        # Make a ConstGpuModule as a CustomConst
        assert len(args) == 1
        ctx_arg = args[0]
        ctx_wire = self.builder.add_op(convert_itousize(), ctx_arg)

        ctx_ty = GPU_EXTENSION.get_type("context").instantiate([])
        get_ctx_op = ops.ExtOp(
            GPU_EXTENSION.get_op("get_context"),
            ht.FunctionType([ht.USize()], [ht.Option(ctx_ty)]),
        )
        node = self.builder.add_op(get_ctx_op, ctx_wire)
        opt_w: Wire = node[0]
        err = "Failed to spawn GPU context"
        out_node = build_unwrap(self.builder, opt_w, err)
        return CallReturnWires(regular_returns=[out_node], inout_returns=[])


class GpuModuleDiscardCompiler(CustomInoutCallCompiler):
    """Compiler for discarding GPU contexts."""

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        assert len(args) == 1
        ctx = args[0]
        op = GPU_EXTENSION.get_op("dispose_context").instantiate([])
        self.builder.add_op(op, ctx)
        return CallReturnWires(regular_returns=[], inout_returns=[])


class GpuModuleCallCompiler(CustomInoutCallCompiler):
    """Compiler for GPU calls
    When a GPU method is called in guppy, we turn it into 2 tket2 ops:
    * lookup: gpu.module -> gpu.func
    * call: gpu.context * gpu.func * inputs -> gpu.context * output

    For the gpu.module that we use in lookup, a constant is created for each
    call, using the gpu file information embedded in method's `self` argument.
    """

    fn_name: str

    def __init__(self, name: str) -> None:
        self.fn_name = name

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        # The arguments should be:
        # - a GPU context
        # - any args meant for the GPU function
        assert len(args) >= 1
        module_ty = GPU_EXTENSION.get_type("module").instantiate([])
        ctx_ty = GPU_EXTENSION.get_type("context").instantiate([])

        fn_name_arg = ht.StringArg(self.fn_name)
        # Function type without Inout context arg (for building)
        assert isinstance(self.node, GlobalCall)
        assert self.func is not None
        gpu_sig = FunctionType(
            self.func.ty.inputs[1:],
            self.func.ty.output,
        ).to_hugr(self.ctx)

        inputs_row_arg = ht.ListArg([ty.type_arg() for ty in gpu_sig.input])
        output_row_arg = ht.ListArg([ty.type_arg() for ty in gpu_sig.output])

        func_ty = GPU_EXTENSION.get_type("func").instantiate(
            [inputs_row_arg, output_row_arg]
        )
        future_ty = FUTURES_EXTENSION.get_type("Future").instantiate(
            [ht.Tuple(*gpu_sig.output).type_arg()]
        )

        # Get the module information from the type
        selfarg = self.func.ty.inputs[0].ty
        if info := gpu_module_info(selfarg):
            const_module = self.builder.add_const(ConstGpuModule(*info))
        else:
            raise InternalGuppyError(
                "Expected cached signature to have GPU module as first arg"
            )

        gpu_module = self.builder.load(const_module)

        # Lookup the function we want
        gpu_opdef = GPU_EXTENSION.get_op("lookup").instantiate(
            [fn_name_arg, inputs_row_arg, output_row_arg],
            ht.FunctionType([module_ty], [func_ty]),
        )
        gpu_func = self.builder.add_op(gpu_opdef, gpu_module)

        # Call the function
        call_op = GPU_EXTENSION.get_op("call").instantiate(
            [inputs_row_arg, output_row_arg],
            ht.FunctionType([ctx_ty, func_ty, *gpu_sig.input], [ctx_ty, future_ty]),
        )

        ctx, future = self.builder.add_op(call_op, args[0], gpu_func, *args[1:])

        read_opdef = FUTURES_EXTENSION.get_op("Read").instantiate(
            [ht.Tuple(*gpu_sig.output).type_arg()],
            ht.FunctionType([future_ty], [ht.Tuple(*gpu_sig.output)]),
        )
        result = self.builder.add_op(read_opdef, future)
        ws: list[Wire] = list(result[:])
        node = self.builder.add_op(ops.UnpackTuple(gpu_sig.output), *ws)
        ws: list[Wire] = list(node[:])

        return CallReturnWires(regular_returns=ws, inout_returns=[ctx])
