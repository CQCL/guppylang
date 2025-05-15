
import hugr.std
from hugr import Wire, ops
from hugr import tys as ht
from hugr.std.int import IntVal
from tket2.extension import ConstWasmModule
from tket2.extensions import wasm

from guppylang.definition.ty import WasmModule
from guppylang.definition.value import CallReturnWires
from guppylang.std._internal.compiler.prelude import build_unwrap
from guppylang.tys.ty import (
    NumericType,
)


class WasmCompiler(CustomInoutCallCompiler):
    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        outs = 1
        ctx = 0
        return CallReturnWires(regular_returns=args[outs:], inout_returns=[args[ctx]])


# Compiler for initialising WASM modules
class WasmModuleCompiler(CustomInoutCallCompiler):
    defn: WasmModule

    def __init__(self, defn: WasmModule) -> None:
        self.defn = defn

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        # Make a ConstWasmModule as a CustomConst
        assert args == []
        module = ConstWasmModule(self.defn.wasm_file, self.defn.wasm_hash)
        w = wasm()
        op = w.get_op("get_context").instantiate([])
        val = IntVal(self.defn.ctx_id, NumericType.INT_WIDTH)
        k = self.builder.add_const(val)
        # hugr-py doesn't yet export a method to load a usize directly?
        ctx_id_nat = self.builder.load(k)
        convert_op = ops.ExtOp(
            hugr.std.int.CONVERSIONS_EXTENSION.get_op("itousize"),
            ht.FunctionType([hugr.std.int.int_t(NumericType.INT_WIDTH)], [ht.USize()]),
        )
        ctx_id_usize = self.builder.add_op(convert_op, ctx_id_nat)

        ws = self.builder.add_op(op, ctx_id_usize)
        assert len(ws) == 1
        # Assumptions:
        #  * get_context will fail iff the ctx_id has already been used
        #  * GuppyModule is making sure we never try to make 2 contexts with the same ctx_id
        #  * So, this option should always be some(ctx)
        err = "WASM Context creation failed"
        ctx = build_unwrap(self.builder, ws[0], err).outputs()
        return CallReturnWires(regular_returns=[ctx], inout_returns=[])


# Compiler for initialising WASM modules
class WasmModuleDiscardCompiler(CustomInoutCallCompiler):
    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        assert len(args) == 1
        ctx = args[0]
        w = wasm()
        op = w.get_op("dispose_context").instantiate([])
        self.builder.add_op(op, ctx)
        return CallReturnWires(regular_returns=[], inout_returns=[])
