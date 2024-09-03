"""A hugr extension with guppy-specific operations."""

from collections.abc import Sequence
from dataclasses import dataclass

import hugr.ext as he
import hugr.tys as ht
from hugr import ops

from guppylang.tys.ty import FunctionType, Type

EXTENSION: he.Extension = he.Extension("guppylang", he.Version(0, 1, 0))


PARTIAL_OP_DEF: he.OpDef = EXTENSION.add_op_def(
    he.OpDef(
        "partial",
        signature=he.OpDefSig(
            poly_func=None,
            binary=True,
        ),
        description="A partial application of a function.\n"
        "Given arguments [*a],[*b],[*c], represents an operation with type\n"
        "`(*c, *a -> *b), *c -> (*a -> *b)`",
    )
)


@dataclass
class PartialOp(ops.AsExtOp):
    """An operation that partially evaluates a function.

    args:
        captured_inputs: A list of input types `c_0, ..., c_k` to partially apply.
        other_inputs: A list of input types `a_0, ..., a_n` not partially applied.
        outputs: The output types `b_0, ..., b_m` of the partially applied function.

    returns:
        An operation with type
            ` (c_0, ..., c_k, a_0, ..., a_n -> b_0, ..., b_m ), c_0, ..., c_k`
            `-> (a_0, ..., a_n -> b_0, ..., b_m)`
    """

    captured_inputs: list[Type]
    other_inputs: list[Type]
    outputs: list[Type]

    def from_closure(
        self, closure_ty: ht.FunctionType, captured_tys: Sequence[ht.Type]
    ) -> "PartialOp":
        """An operation that partially evaluates a function.

        args:
            closure_ty: A function `(c_0, ..., c_k, a_0, ..., a_n) -> b_0, ..., b_m`
            captured_tys: A list `c_0, ..., c_k` of types captured by the function

        returns:
            An operation with type
                ` (c_0, ..., c_k, a_0, ..., a_n -> b_0, ..., b_m ), c_0, ..., c_k`
                `-> (a_0, ..., a_n -> b_0, ..., b_m)`
        """
        assert len(closure_ty.input) >= len(captured_tys)
        assert captured_tys == closure_ty.input[: len(captured_tys)]

        other_inputs = closure_ty.input[len(captured_tys) :]
        return PartialOp(
            captured_inputs=captured_tys,
            other_inputs=other_inputs,
            outputs=closure_ty.output,
        )

    def op_def(self) -> he.OpDef:
        return PARTIAL_OP_DEF

    def type_args(self) -> list[ht.TypeArg]:
        captured_args = [ht.TypeArg(ty) for ty in self.captured_inputs]
        other_args = [ht.TypeArg(ty) for ty in self.other_inputs]
        output_args = [ht.TypeArg(ty) for ty in self.outputs]
        return (
            [
                captured_args,
                other_args,
                output_args,
            ],
        )

    def cached_signature(self) -> ht.FunctionType | None:
        closure_ty = FunctionType(
            [*self.captured_inputs, *self.other_inputs],
            self.outputs,
        )
        return ht.FunctionType([closure_ty, *self.captured_inputs], closure_ty.output)

    @classmethod
    def from_ext(cls, custom: ops.ExtOp) -> "PartialOp":
        match custom:
            case ops.ExtOp(
                _op_def=op_def,
                args=[captured_args, other_args, output_args],
            ):
                if op_def.qualified_name() == PARTIAL_OP_DEF.qualified_name():
                    return cls(
                        captured_args=captured_args,
                        other_args=other_args,
                        output_args=output_args,
                    )
        msg = f"Invalid custom op: {custom}"
        raise ops.AsExtOp.InvalidExtOp(msg)
