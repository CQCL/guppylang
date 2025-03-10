from hugr import Wire, ops
from hugr import tys as ht
from hugr.build import function as hf
from hugr.std.int import int_t

from guppylang.compiler.core import GlobalConstId
from guppylang.definition.custom import CustomCallCompiler, CustomInoutCallCompiler
from guppylang.definition.value import CallReturnWires
from guppylang.std._internal.compiler.arithmetic import inarrow_s, iwiden_s
from guppylang.std._internal.compiler.array import array_map, array_type
from guppylang.std._internal.compiler.prelude import (
    build_unwrap,
    build_unwrap_right,
)
from guppylang.std._internal.compiler.quantum import (
    QSYSTEM_RANDOM_EXTENSION,
    QSYSTEM_UTILS_EXTENSION,
    RNGCONTEXT_T,
)
from guppylang.std._internal.util import external_op


class RandomIntCompiler(CustomInoutCallCompiler):
    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        [ctx] = args
        [rnd, ctx] = self.builder.add_op(
            external_op("RandomInt", [], ext=QSYSTEM_RANDOM_EXTENSION)(
                ht.FunctionType([RNGCONTEXT_T], [int_t(5), RNGCONTEXT_T]), []
            ),
            ctx,
        )
        [rnd] = self.builder.add_op(iwiden_s(5, 6), rnd)
        return CallReturnWires(regular_returns=[rnd], inout_returns=[ctx])


class RandomIntBoundedCompiler(CustomInoutCallCompiler):
    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        [ctx, bound] = args
        bound_sum = self.builder.add_op(inarrow_s(6, 5), bound)
        bound = build_unwrap_right(
            self.builder, bound_sum, "bound must be a 32-bit integer"
        )
        [rnd, ctx] = self.builder.add_op(
            external_op("RandomIntBounded", [], ext=QSYSTEM_RANDOM_EXTENSION)(
                ht.FunctionType([RNGCONTEXT_T, int_t(5)], [int_t(5), RNGCONTEXT_T]), []
            ),
            ctx,
            bound,
        )
        [rnd] = self.builder.add_op(iwiden_s(5, 6), rnd)
        return CallReturnWires(regular_returns=[rnd], inout_returns=[ctx])


class RPCCompiler(CustomCallCompiler):
    def compile(self, args: list[Wire]) -> list[Wire]:
        elem_ty = int_t(6)
        elem_opt_ty = ht.Option(elem_ty)
        length = ht.VariableArg(1, ht.BoundedNatParam())
        [request] = args

        # Convert `request` from an array of optional ints to an array of ints
        unwrap_fn = self.builder.load_function(
            self.define_unwrap_fn_helper(elem_ty),
            instantiation=ht.FunctionType([elem_opt_ty], [elem_ty]),
            type_args=[ht.TypeTypeArg(elem_ty)],
        )
        [request] = self.builder.add_op(
            array_map(elem_opt_ty, length, elem_ty), request, unwrap_fn
        )

        [response] = self.builder.add_op(
            external_op("RPC", [], ext=QSYSTEM_UTILS_EXTENSION)(
                ht.FunctionType(
                    [array_type(elem_ty, length)],
                    [array_type(elem_ty, length)],
                ),
                [],
            ),
            request,
        )

        # Convert `response` from an array of ints to an array of optional ints
        wrap_fn = self.builder.load_function(
            self.define_wrap_fn_helper(elem_ty),
            instantiation=ht.FunctionType([elem_ty], [elem_opt_ty]),
            type_args=[ht.TypeTypeArg(elem_ty)],  # TODO: double check the type arg
        )
        [response] = self.builder.add_op(
            array_map(elem_ty, length, elem_opt_ty), response, wrap_fn
        )
        return [response]

    def define_unwrap_fn_helper(self, elem_ty: ht.Type) -> hf.Function:
        func_ty = ht.PolyFuncType(
            params=[ht.TypeTypeParam(ht.TypeBound.Any)],
            body=ht.FunctionType([ht.Option(elem_ty)], [elem_ty]),
        )
        func, already_defined = self.ctx.declare_global_func(
            GlobalConstId.fresh("qsystem.utils.rpc._unwrap.helper"), func_ty
        )
        if not already_defined:
            err_msg = "qsystem.utils.rpc._unwrap: unexpected failure while unwrapping"
            elem = build_unwrap(func, func.inputs()[0], err_msg)
            func.set_outputs(elem)
        return func

    def define_wrap_fn_helper(self, elem_ty: ht.Type) -> hf.Function:
        func_ty = ht.PolyFuncType(
            params=[ht.TypeTypeParam(ht.TypeBound.Any)],
            body=ht.FunctionType([elem_ty], [ht.Option(elem_ty)]),
        )
        func, already_defined = self.ctx.declare_global_func(
            GlobalConstId.fresh("qsystem.utils.rpc._wrap.helper"), func_ty
        )
        if not already_defined:
            elem_opt = func.add_op(ops.Some(elem_ty), func.inputs()[0])
            func.set_outputs(elem_opt)
        return func
