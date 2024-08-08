from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, TypeVar

import hugr
import hugr.std.float
import hugr.std.int
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


def dummy_op(
    name: str,
    inp: Sequence[Any],
    out: Sequence[Any],
    ext: str = "dummy",
    n_vars: int = 0,
) -> ops.DataflowOp:
    """Dummy operation.

    Args:
        op_name: The name of the operation.
        inp: The python input types of the operation.
        out: The python output types of the operation.
        ext: The extension of the operation.
        n_vars: The number of type arguments. Defaults to 0.
    """
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

    # Dummy arguments
    args: list[ht.TypeArg] = [ht.BoundedNatArg(n=NumericType.INT_WIDTH)] * n_vars

    sig = ht.FunctionType(input=input, output=output)
    return ops.Custom(name=name, extension=ext, signature=sig, args=args)


def float_op(
    op_name: str,
    inp: Sequence[Any],
    out: Sequence[Any],
    ext: str = "arithmetic.float",
) -> ops.DataflowOp:
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
    inp: Sequence[Any],
    out: Sequence[Any],
    ext: str = "arithmetic.int",
    n_vars: int = 1,
) -> ops.DataflowOp:
    """Utility method to create Hugr integer arithmetic ops.

    Args:
        op_name: The name of the operation.
        inp: The python input types of the operation.
        out: The python output types of the operation.
        ext: The extension of the operation.
        n_vars: The number of type arguments. Defaults to 1.
    """
    input = [builtin_type_to_hugr(ty) for ty in inp]
    output = [builtin_type_to_hugr(ty) for ty in out]
    # Ideally we'd be able to derive the arguments from the input/output types,
    # but the amount of variables does not correlate with the signature for the
    # integer ops in hugr :/
    # https://github.com/CQCL/hugr/blob/bfa13e59468feb0fc746677ea3b3a4341b2ed42e/hugr-core/src/std_extensions/arithmetic/int_ops.rs#L116
    args: list[ht.TypeArg] = [ht.BoundedNatArg(n=NumericType.INT_WIDTH)] * n_vars
    sig = ht.FunctionType(input=input, output=output)
    return ops.Custom(extension=ext, signature=sig, name=op_name, args=args)


def logic_op(
    op_name: str, args: list[ht.TypeArg] | None = None, *, inputs: int = 2
) -> ops.DataflowOp:
    """Utility method to create Hugr logic ops."""
    args = args or []
    typ: ht.Type
    if not args:
        typ = ht.Bool
    else:
        assert len(args) == 1, "Logic ops should have at most one type argument."
        typ = ht.Variable(idx=0, bound=ht.TypeBound.Any)

    sig = ht.FunctionType(input=[typ for _ in range(inputs)], output=[typ])

    return ops.Custom(extension="logic", signature=sig, name=op_name, args=args)
