"""A hugr extension with guppy-specific operations."""

from collections.abc import Iterator, Sequence
from dataclasses import dataclass

import hugr.ext as he
import hugr.tys as ht
from hugr import ops

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

    captured_inputs: list[ht.Type]
    other_inputs: list[ht.Type]
    outputs: list[ht.Type]

    @classmethod
    def from_closure(
        cls, closure_ty: ht.FunctionType, captured_tys: Sequence[ht.Type]
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
        return cls(
            captured_inputs=list(captured_tys),
            other_inputs=list(other_inputs),
            outputs=list(closure_ty.output),
        )

    def op_def(self) -> he.OpDef:
        return PARTIAL_OP_DEF

    def type_args(self) -> list[ht.TypeArg]:
        captured_args: list[ht.TypeArg] = [
            ht.TypeTypeArg(ty) for ty in self.captured_inputs
        ]
        other_args: list[ht.TypeArg] = [ht.TypeTypeArg(ty) for ty in self.other_inputs]
        output_args: list[ht.TypeArg] = [ht.TypeTypeArg(ty) for ty in self.outputs]
        return [
            ht.SequenceArg(captured_args),
            ht.SequenceArg(other_args),
            ht.SequenceArg(output_args),
        ]

    def cached_signature(self) -> ht.FunctionType | None:
        closure_ty = ht.FunctionType(
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

                    def arg_seq_to_types(args: ht.TypeArg) -> Iterator[ht.Type]:
                        assert isinstance(args, ht.SequenceArg)
                        for arg in args.elems:
                            assert isinstance(arg, ht.TypeTypeArg)
                            yield arg.ty

                    return cls(
                        captured_inputs=[*arg_seq_to_types(captured_args)],
                        other_inputs=[*arg_seq_to_types(other_args)],
                        outputs=[*arg_seq_to_types(output_args)],
                    )
        msg = f"Invalid custom op: {custom}"
        raise ops.AsExtOp.InvalidExtOp(msg)
