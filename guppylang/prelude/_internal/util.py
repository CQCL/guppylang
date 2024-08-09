"""Utilities for defining the with builtin functions.

Note: This is all _really_ hacky, and intended to be temporary until we have a
unified definition of extension operations.
"""

import builtins
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeVar

import hugr
import hugr.std.float
import hugr.std.int
from hugr import ops
from hugr import tys as ht
from hugr import val as hv

import guppylang.tys.builtin
import guppylang.tys.ty
import guppylang.tys.var
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


def var_t(var_idx: int = 0) -> ht.Type:
    """The hugr type for a TypeVar[T].

    args:
        var_idx: The index of `T` in the operation's type arguments.
    """
    return ht.Variable(idx=var_idx, bound=ht.TypeBound.Copyable)


def lvar_t(var_idx: int = 0) -> ht.Type:
    """The hugr type for a linear TypeVar[T].

    args:
        var_idx: The index of `T` in the operation's type arguments.
    """
    return ht.Variable(idx=var_idx, bound=ht.TypeBound.Any)


def list_t(var_idx: int = 0) -> ht.Type:
    """The hugr type for a list[T]

    args:
        var_idx: The index of `T` in the operation's type arguments.
    """
    bound: ht.TypeBound = ht.TypeBound.Copyable
    return ht.Opaque(
        extension="Collections",
        id="List",
        args=[ht.VariableArg(idx=var_idx, param=ht.TypeTypeParam(bound=bound))],
        bound=bound,
    )


def linst_t(var_idx: int = 0) -> ht.Type:
    """The hugr type for a linst[T]

    args:
        var_idx: The index of `T` in the operation's type arguments.
    """
    bound = ht.TypeBound.Any
    return ht.Opaque(
        extension="Collections",
        id="List",
        args=[ht.VariableArg(idx=var_idx, param=ht.TypeTypeParam(bound=bound))],
        bound=bound,
    )


def array_n_t(n_var_idx: int = 0, t_var_idx: int = 1) -> ht.Type:
    """The hugr type for an array[T, n]

    args:
        n_var_idx: The index of `n` in the operation's type arguments.
        t_var_idx: The index of `T` in the operation's type arguments.
    """
    bound: ht.TypeBound = ht.TypeBound.Copyable
    return ht.Opaque(
        extension="prelude",
        id="array",
        args=[
            ht.VariableArg(
                idx=n_var_idx,
                param=ht.BoundedNatParam(upper_bound=hugr.std.int.LOG_WIDTH_BOUND),
            ),
            ht.VariableArg(idx=t_var_idx, param=ht.TypeTypeParam(bound=bound)),
        ],
        bound=bound,
    )


def int_arg(n: int = NumericType.INT_WIDTH) -> ht.TypeArg:
    """A bounded int type argument."""
    return ht.BoundedNatArg(n=n)


def type_arg() -> ht.TypeArg:
    """A generic type argument."""
    return ht.VariableArg(idx=0, param=ht.TypeTypeParam(bound=ht.TypeBound.Copyable))


def ltype_arg() -> ht.TypeArg:
    """A generic linear type argument."""
    return ht.VariableArg(idx=0, param=ht.TypeTypeParam(bound=ht.TypeBound.Any))


def builtin_type_to_hugr(ty: builtins.type) -> ht.Type:
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


def type_to_hugr(ty: guppylang.tys.ty.Type | builtins.type | ht.Type) -> ht.Type:
    """Translates either a guppylang type or a native python type to a Hugr type.

    Raises a ValueError if the builtin type is not supported.
    """
    if isinstance(ty, ht.Type):
        return ty
    elif isinstance(ty, guppylang.tys.ty.TypeBase):
        return ty.to_hugr()
    else:
        assert isinstance(ty, builtins.type), f"Unsupported type: {ty}"
        return builtin_type_to_hugr(ty)


def dummy_op(
    name: str,
    inp: Sequence[guppylang.tys.ty.Type | builtins.type | ht.Type],
    out: Sequence[guppylang.tys.ty.Type | builtins.type | ht.Type],
    ext: str = "dummy",
    args: list[ht.TypeArg] | None = None,
) -> ops.DataflowOp:
    """Dummy operation.

    Args:
        op_name: The name of the operation.
        inp: The input types of the operation.
            If the types are guppylang types, they are translated to Hugr types.
            Any other types is treated as a native python type, and translated to
            a Hugr type using `builtin_type_to_hugr`.
        out: The output types of the operation.
            If the types are guppylang types, they are translated to Hugr types.
            Any other types is treated as a native python type, and translated to
            a Hugr type using `builtin_type_to_hugr`.
        ext: The extension of the operation.
        args: The type arguments of the operation.
    """
    # TODO: Using this function as a placeholder until we know if it can be
    # dropped with the builder update.
    try:
        input = [type_to_hugr(ty) for ty in inp]
        output = [type_to_hugr(ty) for ty in out]
    except ValueError as e:
        e.add_note(f"For function {name}")
        raise

    args = args or []

    sig = ht.FunctionType(input=input, output=output)
    return ops.Custom(name=name, extension=ext, signature=sig, args=args)


def float_op(
    op_name: str,
    inp: Sequence[guppylang.tys.ty.Type | builtins.type | ht.Type],
    out: Sequence[guppylang.tys.ty.Type | builtins.type | ht.Type],
    ext: str = "arithmetic.float",
) -> ops.DataflowOp:
    """Utility method to create Hugr float arithmetic ops.

    Args:
        op_name: The name of the operation.
        inp: The python input types of the operation.
        out: The python output types of the operation.
        ext: The extension of the operation.
    """
    input = [type_to_hugr(ty) for ty in inp]
    output = [type_to_hugr(ty) for ty in out]
    sig = ht.FunctionType(input=input, output=output)
    return ops.Custom(extension=ext, signature=sig, name=op_name, args=[])


def int_op(
    op_name: str,
    inp: Sequence[guppylang.tys.ty.Type | builtins.type | ht.Type],
    out: Sequence[guppylang.tys.ty.Type | builtins.type | ht.Type],
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
    input = [type_to_hugr(ty) for ty in inp]
    output = [type_to_hugr(ty) for ty in out]
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
