"""Compilers for  angle operations from the tket2 extension."""

from typing import ClassVar

from hugr import Wire, ops
from hugr import tys as ht
from hugr import val as hv
from hugr.std.float import FLOAT_T

# from guppylang.compiler.hugr_extension import UnsupportedOp
from guppylang.prelude._internal.compiler.arithmetic import (
    convert_itousize,
    convert_ifromusize,
)
from guppylang.prelude._internal.compiler.quantum import ANGLE_EXTENSION, ANGLE_T
from guppylang.definition.custom import (
    CustomCallCompiler,
)
from guppylang.tys.ty import NumericType


class AngleOpCompiler(CustomCallCompiler):
    """Compiler for tket2 angle ops.

    Automatically translated between the Hugr usize type used in the angle extension
    and Guppy's `nat` type.
    """

    NAT_TYPE: ClassVar[ht.Type] = NumericType(NumericType.Kind.Nat).to_hugr()

    def __init__(self, op_name: str) -> None:
        self.op_name = op_name

    def nat_to_usize(self, value: Wire) -> Wire:
        return self.builder.add_op(convert_itousize(), value)

    def usize_to_nat(self, value: Wire) -> Wire:
        return self.builder.add_op(convert_ifromusize(), value)

    def compile(self, args: list[Wire]) -> list[Wire]:
        sig = ht.FunctionType(self.ty.input.copy(), self.ty.output.copy())
        for i, ty in enumerate(sig.input):
            if ty == self.NAT_TYPE:
                args[i] = self.nat_to_usize(args[i])
                sig.input[i] = ht.USize()
        for i, ty in enumerate(sig.output):
            if ty == self.NAT_TYPE:
                sig.output[i] = ht.USize()
        op = ops.ExtOp(ANGLE_EXTENSION.get_op(self.op_name), sig, [])
        outs: list[Wire] = [*self.builder.add_op(op, *args)]
        for i, ty in enumerate(sig.output):
            if ty == ht.USize():
                outs[i] = self.usize_to_nat(outs[i])
        return outs


class AfromradCompiler(CustomCallCompiler):
    def compile(self, args: list[Wire]) -> list[Wire]:
        # TODO how to do this properly?
        log_denom = self.builder.load(
            hv.Extension(
                name="ConstUsize", typ=ht.USize(), val=0, extensions=["prelude"]
            )
        )
        op = ops.ExtOp(
            ANGLE_EXTENSION.get_op("afromrad"),
            ht.FunctionType([ht.USize(), FLOAT_T], [ANGLE_T]),
            [],
        )
        return [self.builder.add_op(op, log_denom, *args)]
