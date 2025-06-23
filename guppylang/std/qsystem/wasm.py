from collections.abc import Callable
from typing import no_type_check

from hugr import Wire
from tket2.extensions import wasm

from guppylang.decorator import guppy
from guppylang.definition.custom import CustomInoutCallCompiler
from guppylang.definition.value import CallReturnWires
from guppylang.std.builtins import array, comptime, nat


class WasmCompiler(CustomInoutCallCompiler):
    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        outs = 1
        ctx = 0
        return CallReturnWires(regular_returns=args[outs:], inout_returns=[args[ctx]])


# Compiler for initialising WASM modules
class WasmModuleDiscardCompiler(CustomInoutCallCompiler):
    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        assert len(args) == 1
        ctx = args[0]
        w = wasm()
        op = w.get_op("dispose_context").instantiate([])
        self.builder.add_op(op, ctx)
        return CallReturnWires(regular_returns=[], inout_returns=[])


T = guppy.type_var("T", copyable=False, droppable=False)


@guppy
@no_type_check
def spawn_wasm_contexts(n: nat @ comptime, spawn: Callable[[nat], T]) -> "array[T, n]":  # noqa: F821
    return array(spawn(nat(ix)) for ix in range(n))
