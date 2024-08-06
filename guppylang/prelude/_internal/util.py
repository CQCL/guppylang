from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, TypeVar

import hugr
from hugr import ops
from hugr import tys as ht
from hugr import val as hv

from guppylang.tys.builtin import list_type
from guppylang.tys.ty import NumericType, Type


@dataclass
class ListVal(hv.ExtensionValue):
    """Custom value for a floating point number."""

    v: list[hv.Value]
    ty: Type

    def to_value(self) -> hv.Extension:
        typ = list_type(self.ty).to_hugr()
        return hv.Extension(
            name="ListValue", typ=typ, val=self.v, extensions=["Collections"]
        )


def builtin_type_to_hugr(ty: Any) -> ht.Type:
    """Utility function to translate numeric python types to Hugr types.

    Supports only a handful types, used in the builtin operations.
    """
    from guppylang.prelude.builtins import nat

    if ty is int or ty is nat:
        return hugr.std.int.int_t(NumericType.INT_WIDTH)
    elif ty is float:
        return hugr.std.float.FLOAT_T
    elif ty is bool:
        return ht.Bool
    elif ty is TypeVar:
        return ht.Variable(idx=0, bound=ht.TypeBound.Any)
    else:
        raise ValueError(f"Unsupported type: {ty}")


def dummy_op(name: str, inp: Sequence[Any], out: Sequence[Any]) -> ops.Op:
    """Dummy operation."""
    # TODO: Using this function as a placeholder until we know if it can be
    # dropped with the builder update.
    try:
        input = [builtin_type_to_hugr(ty) for ty in inp]
    except ValueError:
        # Just ignore for now (e.g. for lists)
        input = []

    try:
        output = [builtin_type_to_hugr(ty) for ty in out]
    except ValueError:
        # Just ignore for now (e.g. for lists)
        output = []

    sig = ht.FunctionType(input=input, output=output)
    return ops.Custom(name=name, extension="dummy", signature=sig, args=[])


def float_op(
    op_name: str,
    inp: Sequence[Any],
    out: Sequence[Any],
    ext: str = "arithmetic.float",
) -> ops.Op:
    """Utility method to create Hugr float arithmetic ops.

    Args:
        op_name: The name of the operation.
        inp: The python input types of the operation.
        out: The python output types of the operation.
        ext: The extension of the operation.
    """
    input = [builtin_type_to_hugr(ty) for ty in inp]
    output = [builtin_type_to_hugr(ty) for ty in out]
    sig = ht.FunctionType(input=input, output=output)
    return ops.Custom(extension=ext, signature=sig, name=op_name, args=[])


def int_op(
    op_name: str,
    ext: str = "arithmetic.int",
    *,
    args: list[ht.TypeArg] | None = None,
    num_params: int = 1,
) -> ops.Op:
    """Utility method to create Hugr integer arithmetic ops.

    Args:
        op_name: The name of the operation.
        ext: The extension of the operation.
        num_params: The number of type parameters.
        args: The type arguments of the operation.
            If not provided, it defaults to `num_params` type parameters.
    """
    # TODO: Why do we need arguments here?
    #     Can't we just accept some `input` and `output` type rows?

    if args is None:
        args = num_params * [ht.BoundedNatArg(n=NumericType.INT_WIDTH)]
    else:
        num_params = len(args)
    assert (
        num_params > 0
    ), "Integer ops should have at least one type parameter."  # TODO: Why?

    output = [ht.Variable(idx=0, bound=ht.TypeBound.Any)]
    input = [ht.Variable(idx=i, bound=ht.TypeBound.Any) for i in range(len(args))]

    sig = ht.FunctionType(input=input, output=output)
    return ops.Custom(extension=ext, signature=sig, name=op_name, args=args)


def logic_op(
    op_name: str, args: list[ht.TypeArg] | None = None, *, inputs: int = 2
) -> ops.Op:
    """Utility method to create Hugr logic ops."""
    args = args or []
    typ: ht.Type
    if not args:
        typ = ht.Bool()
    else:
        assert len(args) == 1, "Logic ops should have at most one type argument."
        ht.Variable(idx=0, bound=ht.TypeBound.Any)

    sig = ht.FunctionType(input=[typ for _ in range(inputs)], output=[typ])

    return ops.Custom(extension="logic", signature=sig, name=op_name, args=args)
