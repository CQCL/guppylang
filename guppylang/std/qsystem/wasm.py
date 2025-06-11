from typing import Callable

import hugr.std
from hugr import Wire, ops
from hugr import tys as ht
from hugr.std.int import IntVal
from tket2.extensions import wasm

from guppylang.module import GuppyModule
from guppylang.decorator import guppy
from guppylang.definition.custom import CustomInoutCallCompiler
from guppylang.definition.value import CallReturnWires
#from guppylang.definition.wasm import WasmModule
from guppylang.std.builtins import nat, array
from guppylang.tys.builtin import wasm_module_to_hugr, wasm_module_type_def
from guppylang.tys.ty import (
    NumericType,
)

qsystem_wasm = GuppyModule("qsystem_wasm")

class WasmCompiler(CustomInoutCallCompiler):
    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        outs = 1
        ctx = 0
        return CallReturnWires(regular_returns=args[outs:], inout_returns=[args[ctx]])


# Compiler for initialising WASM modules
#class WasmModuleCompiler(CustomInoutCallCompiler):
#    defn: WasmModule
#
#    def __init__(self, defn: WasmModule) -> None:
#        self.defn = defn
#
#    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
#        # Make a ConstWasmModule as a CustomConst
#        assert args == []
#        w = wasm()
#        op = w.get_op("get_context").instantiate([])
#        val = IntVal(self.defn.ctx_id, NumericType.INT_WIDTH)
#        k = self.builder.add_const(val)
#        # hugr-py doesn't have a method to load a usize directly, so convert an int
#        ctx_id_nat = self.builder.load(k)
#        convert_op = ops.ExtOp(
#            hugr.std.int.CONVERSIONS_EXTENSION.get_op("itousize"),
#            ht.FunctionType([hugr.std.int.int_t(NumericType.INT_WIDTH)], [ht.USize()]),
#        )
#        ctx_id_usize = self.builder.add_op(convert_op, ctx_id_nat)
#
#        w: Wire = self.builder.add_op(op, ctx_id_usize)
#        return CallReturnWires(regular_returns=[w], inout_returns=[])


# Compiler for initialising WASM modules
class WasmModuleDiscardCompiler(CustomInoutCallCompiler):
    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        assert len(args) == 1
        ctx = args[0]
        w = wasm()
        op = w.get_op("dispose_context").instantiate([])
        self.builder.add_op(op, ctx)
        return CallReturnWires(regular_returns=[], inout_returns=[])


#@guppy.extend_type(wasm_module_type_def, module=qsystem_wasm)
@guppy.type(lambda args: wasm_module_to_hugr(wasm_module_type_def, args), copyable=False, droppable=False, module=qsystem_wasm)
class WasmModule:
    def foo(self: 'WasmModule') -> 'WasmModule':
        return self


N = guppy.nat_var('N')

@guppy(qsystem_wasm)
def foo(w: WasmModule) -> WasmModule:
    return w

@guppy(qsystem_wasm)
def spawn_wasm_contexts(w: Callable[nat, WasmModule]) -> array[WasmModule, N]:
    pass
