from hugr import Wire, ops
from hugr import tys as ht
from hugr.build import function as hf
from hugr.build.dfg import DfBase
from hugr.std.int import int_t

from guppylang.compiler.core import CompilerContext, GlobalConstId
from guppylang.definition.custom import CustomInoutCallCompiler
from guppylang.definition.value import CallReturnWires
from guppylang.std._internal.compiler.arithmetic import inarrow_s, iwiden_s
from guppylang.std._internal.compiler.array import array_map, array_type
from guppylang.std._internal.compiler.prelude import build_unwrap, build_unwrap_right
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


class OrderInZonesCompiler(CustomInoutCallCompiler):
    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        [option_qubits] = args
        elem_ty = ht.BoundedNatArg(16)

        # unwrap option array to be passed to OrderInZones
        qubits = add_unwrap_op(self.ctx, self.builder, option_qubits, ht.Qubit, elem_ty)

        [qubits] = self.builder.add_op(
            external_op("OrderInZones", [], ext=QSYSTEM_UTILS_EXTENSION)(
                ht.FunctionType(
                    [array_type(ht.Qubit, elem_ty)],
                    [array_type(ht.Qubit, elem_ty)],
                ),
                [],
            ),
            qubits,
        )

        # rewrap array returned from OrderInZones
        option_qubits = add_wrap_op(self.ctx, self.builder, qubits, ht.Qubit, elem_ty)
        return CallReturnWires(regular_returns=[], inout_returns=[option_qubits])


# ------------------------------------------------------
# ---- Helper functions for (un)wrapping arrays -----
# ------------------------------------------------------


def add_unwrap_op(
    ctx: CompilerContext,
    builder: DfBase[ops.DfParentOp],
    option_array: Wire,
    elem_ty: ht.Type,
    length: ht.TypeArg,
) -> Wire:
    def define_unwrap_fn_helper(ctx: CompilerContext, elem_ty: ht.Type) -> hf.Function:
        func_ty = ht.PolyFuncType(
            params=[ht.TypeTypeParam(ht.TypeBound.Any)],
            body=ht.FunctionType([ht.Option(elem_ty)], [elem_ty]),
        )
        func, already_defined = ctx.declare_global_func(
            GlobalConstId.fresh("qsystem.utils._unwrap.helper"), func_ty
        )
        if not already_defined:
            err_msg = "qsystem.utils._unwrap: unexpected failure while unwrapping"
            elem = build_unwrap(func, func.inputs()[0], err_msg)
            func.set_outputs(elem)
        return func

    elem_opt_ty = ht.Option(elem_ty)
    unwrap_fn = builder.load_function(
        define_unwrap_fn_helper(ctx, elem_ty),
        instantiation=ht.FunctionType([elem_opt_ty], [elem_ty]),
        type_args=[ht.TypeTypeArg(elem_ty)],
    )
    [unwrapped_array] = builder.add_op(
        array_map(elem_opt_ty, length, elem_ty), option_array, unwrap_fn
    )
    return unwrapped_array


def add_wrap_op(
    ctx: CompilerContext,
    builder: DfBase[ops.DfParentOp],
    unwrapped_array: Wire,
    elem_ty: ht.Type,
    length: ht.TypeArg,
) -> Wire:
    def define_wrap_fn_helper(ctx: CompilerContext, elem_ty: ht.Type) -> hf.Function:
        func_ty = ht.PolyFuncType(
            params=[ht.TypeTypeParam(ht.TypeBound.Any)],
            body=ht.FunctionType([elem_ty], [ht.Option(elem_ty)]),
        )
        func, already_defined = ctx.declare_global_func(
            GlobalConstId.fresh("qsystem.utils._wrap.helper"), func_ty
        )
        if not already_defined:
            elem_opt = func.add_op(ops.Some(elem_ty), func.inputs()[0])
            func.set_outputs(elem_opt)
        return func

    elem_opt_ty = ht.Option(elem_ty)
    wrap_fn = builder.load_function(
        define_wrap_fn_helper(ctx, elem_ty),
        instantiation=ht.FunctionType([elem_ty], [elem_opt_ty]),
        type_args=[ht.TypeTypeArg(elem_ty)],
    )
    [wrapped_array] = builder.add_op(
        array_map(elem_ty, length, elem_opt_ty), unwrapped_array, wrap_fn
    )
    return wrapped_array
