"""Utilities for defining builtin functions.

Note: This is all _really_ hacky, and intended to be temporary until we have a
unified definition of extension operations.
"""

import builtins
from collections.abc import Callable, Sequence
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
from guppylang.tys.arg import Argument, TypeArg
from guppylang.tys.builtin import int_type, list_type
from guppylang.tys.subst import Inst
from guppylang.tys.ty import NumericType, Type


@dataclass
class ListVal(hv.ExtensionValue):
    """Custom value for a floating point number."""

    v: list[hv.Value]
    ty: ht.Type

    def __init__(self, v: list[hv.Value], elem_ty: Type) -> None:
        self.v = v
        self.ty = list_type(elem_ty).to_hugr()

    def to_value(self) -> hv.Extension:
        # The value list must be serialized at this point, otherwise the
        # `Extension` will not be serializable.
        vs = [v.to_serial_root() for v in self.v]
        return hv.Extension(
            name="ListValue", typ=self.ty, val=vs, extensions=["Collections"]
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
    """The hugr type `array[n, T]` corresponding to the guppy type `array[T, n]`.

    Note that the type arguments are reversed.

    args:
        n_var_idx: The index of `n` in the hugr operation's type arguments.
        t_var_idx: The index of `T` in the hugr operation's type arguments.
    """
    bound: ht.TypeBound = ht.TypeBound.Copyable
    return ht.Opaque(
        extension="prelude",
        id="array",
        args=[
            ht.VariableArg(
                idx=n_var_idx,
                param=ht.BoundedNatParam(upper_bound=None),
            ),
            ht.VariableArg(idx=t_var_idx, param=ht.TypeTypeParam(bound=bound)),
        ],
        bound=bound,
    )


def int_arg(n: int = NumericType.INT_WIDTH) -> ht.TypeArg:
    """A bounded int type argument."""
    return ht.BoundedNatArg(n=n)


def type_arg(idx: int = 0) -> ht.TypeArg:
    """A generic type argument."""
    return ht.VariableArg(idx=idx, param=ht.TypeTypeParam(bound=ht.TypeBound.Copyable))


def ltype_arg(idx: int = 0) -> ht.TypeArg:
    """A generic linear type argument."""
    return ht.VariableArg(idx=idx, param=ht.TypeTypeParam(bound=ht.TypeBound.Any))


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


def make_concrete_arg(
    arg: ht.TypeArg,
    inst: Inst,
    variable_remap: dict[int, int] | None = None,
) -> ht.TypeArg:
    """Makes a concrete hugr type argument using a guppy instantiation.

    Args:
        arg: The hugr type argument to make concrete, containing variable arguments.
        inst: The guppy instantiation of the type arguments.
        variable_remap: A mapping from the hugr param variable indices to
            de Bruijn indices in the guppy type. Defaults to identity.
    """
    remap = variable_remap or {}

    if isinstance(arg, ht.VariableArg) and remap.get(arg.idx, arg.idx) < len(inst):
        concrete_arg: Argument = inst[remap.get(arg.idx, arg.idx)]
        return concrete_arg.to_hugr()
    return arg


def make_concrete(
    ty: ht.Type,
    inst: Inst,
    variable_remap: dict[int, int] | None = None,
) -> ht.Type:
    """Makes a concrete hugr type using a guppy instantiation.

    Args:
        ty: The hugr type to make concrete.
        inst: The guppy instantiation of the type arguments.
        variable_remap: A mapping from the hugr param variable indices to
            de Bruijn indices in the guppy type. Defaults to identity.
    """
    remap = variable_remap or {}

    if isinstance(ty, ht.Variable) and remap.get(ty.idx, ty.idx) < len(inst):
        concrete_arg: Argument = inst[remap.get(ty.idx, ty.idx)]
        assert isinstance(
            concrete_arg, TypeArg
        ), f"Cannot translate const type {concrete_arg} arg into a type"
        return concrete_arg.ty.to_hugr()
    elif isinstance(ty, ht.Opaque):
        # TODO: This is a temporary hack to compute bounds that depend on the
        # type parameters. This won't be needed once we start using hugr's
        # extension definitions, which include a `TypeDefBound` field to compute
        # bounds during instantiation.
        if ty.id == "List":
            assert isinstance(inst[0], TypeArg)
            bound = inst[0].ty.hugr_bound
        else:
            bound = ty.bound

        return ht.Opaque(
            id=ty.id,
            bound=bound,
            extension=ty.extension,
            args=[make_concrete_arg(arg, inst, remap) for arg in ty.args],
        )
    elif isinstance(ty, ht.ExtType):
        return ht.ExtType(
            type_def=ty.type_def,
            args=[make_concrete_arg(arg, inst, remap) for arg in ty.args],
        )
    return ty


def custom_op(
    name: str,
    inp: Sequence[guppylang.tys.ty.Type | builtins.type | ht.Type],
    out: Sequence[guppylang.tys.ty.Type | builtins.type | ht.Type],
    args: list[ht.TypeArg],
    *,
    ext: str = "guppy.unsupported",
    variable_remap: dict[int, int] | None = None,
) -> Callable[[Inst], ops.DataflowOp]:
    """Custom hugr operation

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
        args: The type arguments of the operation.
        ext: The extension of the operation. Defaults to a placeholder extension.
        variable_remap: A mapping from the hugr param variable indices to
            de Bruijn indices in the guppy type. Defaults to identity.

    Returns:
        A function that takes an instantiation of the type arguments and returns
        a concrete HUGR op.
    """
    input = [type_to_hugr(ty) for ty in inp]
    output = [type_to_hugr(ty) for ty in out]

    def op(inst: Inst) -> ops.DataflowOp:
        concrete_input = [make_concrete(ty, inst, variable_remap) for ty in input]
        concrete_output = [make_concrete(ty, inst, variable_remap) for ty in output]
        sig = ht.FunctionType(input=concrete_input, output=concrete_output)

        concrete_args = [make_concrete_arg(arg, inst, variable_remap) for arg in args]

        return ops.Custom(extension=ext, signature=sig, name=name, args=concrete_args)

    return op


def list_op(
    op_name: str,
    inp: Sequence[guppylang.tys.ty.Type | builtins.type | ht.Type],
    out: Sequence[guppylang.tys.ty.Type | builtins.type | ht.Type],
    ext: str = "guppy.unsupported",
) -> Callable[[Inst], ops.DataflowOp]:
    """Utility method to create Hugr list operations.

    These ops have exactly one type argument, used to instantiate the list type.
    If a the input or output types contain some variable type with index 0, it
    is replaced with the type argument when instantiating the op.

    Args:
        op_name: The name of the operation.
        inp: The python input types of the operation.
        out: The python output types of the operation.
        ext: The extension of the operation.

    Returns:
        A function that takes an instantiation of the type arguments and returns
        a concrete HUGR op.
    """
    return custom_op(
        op_name, inp, out, args=[type_arg(0)], ext=ext, variable_remap=None
    )


def linst_op(
    op_name: str,
    inp: Sequence[guppylang.tys.ty.Type | builtins.type | ht.Type],
    out: Sequence[guppylang.tys.ty.Type | builtins.type | ht.Type],
    ext: str = "guppy.unsupported",
) -> Callable[[Inst], ops.DataflowOp]:
    """Utility method to create linear Hugr list operations.

    These ops have exactly one type argument, used to instantiate the list type.
    If a the input or output types contain some variable type with index 0, it
    is replaced with the type argument when instantiating the op.

    Args:
        op_name: The name of the operation.
        inp: The python input types of the operation.
        out: The python output types of the operation.
        ext: The extension of the operation.

    Returns:
        A function that takes an instantiation of the type arguments and returns
        a concrete HUGR op.
    """
    return custom_op(
        op_name, inp, out, args=[ltype_arg(0)], ext=ext, variable_remap=None
    )


def float_op(
    op_name: str,
    inp: Sequence[guppylang.tys.ty.Type | builtins.type | ht.Type],
    out: Sequence[guppylang.tys.ty.Type | builtins.type | ht.Type],
    ext: str = "arithmetic.float",
) -> Callable[[Inst], ops.DataflowOp]:
    """Utility method to create Hugr float arithmetic ops.

    Args:
        op_name: The name of the operation.
        inp: The python input types of the operation.
        out: The python output types of the operation.
        ext: The extension of the operation.

    Returns:
        A function that takes an instantiation of the type arguments and returns
        a concrete HUGR op.
    """
    return custom_op(op_name, inp, out, args=[], ext=ext, variable_remap=None)


def int_op(
    op_name: str,
    inp: Sequence[guppylang.tys.ty.Type | builtins.type | ht.Type],
    out: Sequence[guppylang.tys.ty.Type | builtins.type | ht.Type],
    ext: str = "arithmetic.int",
    n_vars: int = 1,
) -> Callable[[Inst], ops.DataflowOp]:
    """Utility method to create Hugr integer arithmetic ops.

    Args:
        op_name: The name of the operation.
        inp: The python input types of the operation.
        out: The python output types of the operation.
        ext: The extension of the operation.
        n_vars: The number of type arguments. Defaults to 1.

    Returns:
        A function that takes an instantiation of the type arguments and returns
        a concrete HUGR op.
    """
    # Ideally we'd be able to derive the arguments from the input/output types,
    # but the amount of variables does not correlate with the signature for the
    # integer ops in hugr :/
    # https://github.com/CQCL/hugr/blob/bfa13e59468feb0fc746677ea3b3a4341b2ed42e/hugr-core/src/std_extensions/arithmetic/int_ops.rs#L116
    #
    # For now, we just instantiate every type argument to a 64-bit integer.
    args: list[ht.TypeArg] = [int_arg() for _ in range(n_vars)]
    inst = [TypeArg(int_type()) for _ in range(n_vars)]
    concrete_input = [make_concrete(type_to_hugr(ty), inst) for ty in inp]
    concrete_output = [make_concrete(type_to_hugr(ty), inst) for ty in out]

    return custom_op(
        op_name,
        concrete_input,
        concrete_output,
        args=args,
        ext=ext,
        variable_remap=None,
    )


def logic_op(
    op_name: str, inputs: int = 2, parametric_size: bool = True, ext: str = "logic"
) -> Callable[[Inst], ops.DataflowOp]:
    """Utility method to create Hugr logic ops.

    If `parametric_size` is True, the generated operations has a single argument
    encoding the number of boolean inputs to the operation.

    args:
        op_name: The name of the operation.
        inputs: The number of inputs to the operation.
        parametric_size: Whether the size of the input is parametric.
        ext: The extension of the operation.

    Returns:
        A function that takes an instantiation of the type arguments and returns
        a concrete HUGR op.
    """
    inp = [ht.Bool for _ in range(inputs)]
    out = [ht.Bool]
    args = [int_arg(inputs)] if parametric_size else []
    return custom_op(op_name, inp, out, args=args, ext=ext, variable_remap=None)
