"""Compilers building array functions on top of hugr standard operations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeVar

import hugr.std.collections
import hugr.std.int
import hugr.std.prelude
from hugr import Node, Wire, ops
from hugr import tys as ht
from hugr import val as hv

from guppylang.definition.custom import CustomCallCompiler, CustomInoutCallCompiler
from guppylang.definition.value import CallReturnWires
from guppylang.error import InternalGuppyError
from guppylang.tys.builtin import int_type
from guppylang.tys.subst import Inst
from guppylang.tys.ty import type_to_row

if TYPE_CHECKING:
    from collections.abc import Callable

    from hugr.build.dfg import DfBase

    from guppylang.tys.subst import Inst


# --------------------------------------------
# --------------- prelude --------------------
# --------------------------------------------


def error_type() -> ht.ExtType:
    """Returns the hugr type of an error value."""
    return hugr.std.PRELUDE.types["error"].instantiate([])


@dataclass
class ErrorVal(hv.ExtensionValue):
    """Custom value for a floating point number."""

    signal: int
    message: str

    def to_value(self) -> hv.Extension:
        name = "ConstError"
        payload = {"signal": self.signal, "message": self.message}
        return hv.Extension(
            name, typ=error_type(), val=payload, extensions=[hugr.std.PRELUDE.name]
        )

    def __str__(self) -> str:
        return f"Error({self.signal}): {self.message}"


def panic(inputs: list[ht.Type], outputs: list[ht.Type]) -> ops.ExtOp:
    """Returns an operation that panics."""
    op_def = hugr.std.PRELUDE.get_op("panic")
    args: list[ht.TypeArg] = [
        ht.SequenceArg([ht.TypeTypeArg(ty) for ty in inputs]),
        ht.SequenceArg([ht.TypeTypeArg(ty) for ty in outputs]),
    ]
    sig = ht.FunctionType([error_type(), *inputs], outputs)
    return ops.ExtOp(op_def, sig, args)


# ------------------------------------------------------
# --------- Custom compilers for non-native ops --------
# ------------------------------------------------------


def build_panic(
    builder: DfBase[P],
    in_tys: ht.TypeRow,
    out_tys: ht.TypeRow,
    err: Wire,
    *args: Wire,
) -> Node:
    """Builds a panic operation."""
    op = panic(in_tys, out_tys)
    return builder.add_op(op, err, *args)


def build_error(builder: DfBase[P], signal: int, msg: str) -> Wire:
    """Constructs and loads a static error value."""
    val = ErrorVal(signal, msg)
    return builder.load(builder.add_const(val))


# TODO: Common up build_unwrap_right and build_unwrap_left below once
#  https://github.com/CQCL/hugr/issues/1596 is fixed


def build_unwrap_right(
    builder: DfBase[P], either: Wire, error_msg: str, error_signal: int = 1
) -> Node:
    """Unwraps the right value from a `hugr.tys.Either` value, panicking with the given
    message if the result is left.
    """
    conditional = builder.add_conditional(either)
    result_ty = builder.hugr.port_type(either.out_port())
    assert isinstance(result_ty, ht.Sum)
    [left_tys, right_tys] = result_ty.variant_rows
    with conditional.add_case(0) as case:
        error = build_error(case, error_signal, error_msg)
        case.set_outputs(*build_panic(case, left_tys, right_tys, error, *case.inputs()))
    with conditional.add_case(1) as case:
        case.set_outputs(*case.inputs())
    return conditional.to_node()


P = TypeVar("P", bound=ops.DfParentOp)


def build_unwrap_left(
    builder: DfBase[P], either: Wire, error_msg: str, error_signal: int = 1
) -> Node:
    """Unwraps the left value from a `hugr.tys.Either` value, panicking with the given
    message if the result is right.
    """
    conditional = builder.add_conditional(either)
    result_ty = builder.hugr.port_type(either.out_port())
    assert isinstance(result_ty, ht.Sum)
    [left_tys, right_tys] = result_ty.variant_rows
    with conditional.add_case(0) as case:
        case.set_outputs(*case.inputs())
    with conditional.add_case(1) as case:
        error = build_error(case, error_signal, error_msg)
        case.set_outputs(*build_panic(case, right_tys, left_tys, error, *case.inputs()))
    return conditional.to_node()


def build_unwrap(
    builder: DfBase[P], option: Wire, error_msg: str, error_signal: int = 1
) -> Node:
    """Unwraps an `hugr.tys.Option` value, panicking with the given message if the
    result is an error.
    """
    return build_unwrap_right(builder, option, error_msg, error_signal)


def build_expect_none(
    builder: DfBase[P], option: Wire, error_msg: str, error_signal: int = 1
) -> Node:
    """Checks that `hugr.tys.Option` value is `None`, otherwise panics with the given
    message.
    """
    return build_unwrap_left(builder, option, error_msg, error_signal)


class MemSwapCompiler(CustomCallCompiler):
    """Compiler for the `mem_swap` function."""

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        [x, y] = args
        return CallReturnWires(regular_returns=[], inout_returns=[y, x])

    def compile(self, args: list[Wire]) -> list[Wire]:
        raise InternalGuppyError("Call compile_with_inouts instead")


class UnwrapOpCompiler(CustomInoutCallCompiler):
    """Compiler for operations that require unwrapping an single option value result
    which can potentially cause an error.

    Args:
        op: A HUGR operation that outputs an option value.
        err_msg: The error message to be raised if the unwrapped option is an error.
    """

    op: Callable[[ht.FunctionType, Inst], ops.DataflowOp]
    err_msg: str

    def __init__(self, op: Callable[[ht.FunctionType, Inst], ops.DataflowOp], err: str):
        self.op = op
        self.err_msg = err

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        assert len(self.ty.output) == 1
        opt_func_type = ht.FunctionType(
            input=self.ty.input,
            output=[ht.Option(error_type, *self.ty.output)],
        )
        op = self.op(opt_func_type, self.type_args)
        option = self.builder.add_op(op, *args)
        result = build_unwrap(self.builder, option, self.err_msg)
        return CallReturnWires(regular_returns=[result], inout_returns=[])

    def compile(self, args: list[Wire]) -> list[Wire]:
        raise InternalGuppyError("Call compile_with_inouts instead")
