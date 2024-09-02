"""Utilities for defining builtin functions.

Note: These custom definitions will be replaced with direct extension operation
definitions from the hugr library.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from hugr import ops
from hugr import tys as ht
from hugr import val as hv

from guppylang.tys.builtin import list_type
from guppylang.tys.subst import Inst
from guppylang.tys.ty import NumericType, Type

if TYPE_CHECKING:
    from guppylang.tys.arg import Argument


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
        vs = [v._to_serial_root() for v in self.v]
        return hv.Extension(
            name="ListValue", typ=self.ty, val=vs, extensions=["Collections"]
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


def custom_op(
    name: str,
    args: list[ht.TypeArg],
    *,
    ext: str = "guppy.unsupported",
    variable_remap: dict[int, int] | None = None,
) -> Callable[[ht.FunctionType, Inst], ops.DataflowOp]:
    """Custom hugr operation

    Args:
        op_name: The name of the operation.
        args: The type arguments of the operation.
        ext: The extension of the operation. Defaults to a placeholder extension.
        variable_remap: A mapping from the hugr param variable indices to
            de Bruijn indices in the guppy type. Defaults to identity.

    Returns:
        A function that takes an instantiation of the type arguments as well as
        the inferred input and output types and returns a concrete HUGR op.
    """

    def op(ty: ht.FunctionType, inst: Inst) -> ops.DataflowOp:
        concrete_args = [make_concrete_arg(arg, inst, variable_remap) for arg in args]
        return ops.Custom(extension=ext, signature=ty, op_name=name, args=concrete_args)

    return op


def list_op(
    op_name: str,
    ext: str = "guppy.unsupported",
) -> Callable[[ht.FunctionType, Inst], ops.DataflowOp]:
    """Utility method to create Hugr list operations.

    These ops have exactly one type argument, used to instantiate the list type.
    If a the input or output types contain some variable type with index 0, it
    is replaced with the type argument when instantiating the op.

    Args:
        op_name: The name of the operation.
        ext: The extension of the operation.

    Returns:
        A function that takes an instantiation of the type arguments and returns
        a concrete HUGR op.
    """
    return custom_op(op_name, args=[type_arg(0)], ext=ext, variable_remap=None)


def linst_op(
    op_name: str,
    ext: str = "guppy.unsupported",
) -> Callable[[ht.FunctionType, Inst], ops.DataflowOp]:
    """Utility method to create linear Hugr list operations.

    These ops have exactly one type argument, used to instantiate the list type.
    If a the input or output types contain some variable type with index 0, it
    is replaced with the type argument when instantiating the op.

    Args:
        op_name: The name of the operation.
        ext: The extension of the operation.

    Returns:
        A function that takes an instantiation of the type arguments and returns
        a concrete HUGR op.
    """
    return custom_op(op_name, args=[ltype_arg(0)], ext=ext, variable_remap=None)


def float_op(
    op_name: str,
    ext: str = "arithmetic.float",
) -> Callable[[ht.FunctionType, Inst], ops.DataflowOp]:
    """Utility method to create Hugr float arithmetic ops.

    Args:
        op_name: The name of the operation.
        ext: The extension of the operation.

    Returns:
        A function that takes an instantiation of the type arguments and returns
        a concrete HUGR op.
    """
    return custom_op(op_name, args=[], ext=ext, variable_remap=None)


def int_op(
    op_name: str,
    ext: str = "arithmetic.int",
    n_vars: int = 1,
) -> Callable[[ht.FunctionType, Inst], ops.DataflowOp]:
    """Utility method to create Hugr integer arithmetic ops.

    Args:
        op_name: The name of the operation.
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

    return custom_op(
        op_name,
        args=args,
        ext=ext,
        variable_remap=None,
    )


def logic_op(
    op_name: str, parametric_size: bool = True, ext: str = "logic"
) -> Callable[[ht.FunctionType, Inst], ops.DataflowOp]:
    """Utility method to create Hugr logic ops.

    If `parametric_size` is True, the generated operations has a single argument
    encoding the number of boolean inputs to the operation.

    args:
        op_name: The name of the operation.
        parametric_size: Whether the input count is a parameter to the operation.
        ext: The extension of the operation.

    Returns:
        A function that takes an instantiation of the type arguments and returns
        a concrete HUGR op.
    """

    def op(ty: ht.FunctionType, inst: Inst) -> ops.DataflowOp:
        args = [int_arg(len(ty.input))] if parametric_size else []
        return ops.Custom(extension=ext, signature=ty, op_name=op_name, args=args)

    return op
