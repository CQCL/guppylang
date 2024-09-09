"""Compilers for  angle operations from the tket2 extension."""

from typing import ClassVar

from hugr import Wire, ops
from hugr import tys as ht

from guppylang.compiler.hugr_extension import UnsupportedOp
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
        op = ops.Custom(
            op_name="itousize",
            signature=ht.FunctionType([self.NAT_TYPE], [ht.USize()]),
            extension="arithmetic.conversions",
            args=[],
        )
        return self.builder.add_op(op, value)

    def usize_to_nat(self, value: Wire) -> Wire:
        op = ops.Custom(
            op_name="ifromusize",
            signature=ht.FunctionType([self.NAT_TYPE], [ht.USize()]),
            extension="arithmetic.conversions",
            args=[ht.BoundedNatArg(NumericType.INT_WIDTH)],
        )
        return self.builder.add_op(op, value)

    def compile(self, args: list[Wire]) -> list[Wire]:
        sig = ht.FunctionType(self.ty.input.copy(), self.ty.output.copy())
        for i, ty in enumerate(sig.input):
            if ty == self.NAT_TYPE:
                args[i] = self.nat_to_usize(args[i])
                sig.input[i] = ht.USize()
        op = UnsupportedOp(self.op_name, sig.input, sig.output)
        outs: list[Wire] = [*self.builder.add_op(op, *args)]
        for i, ty in enumerate(sig.input):
            if ty == self.NAT_TYPE:
                outs[i] = self.usize_to_nat(outs[i])
                sig.output[i] = ht.USize()
        return outs
