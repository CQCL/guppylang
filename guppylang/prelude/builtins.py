"""Guppy module for builtin types and operations."""

# mypy: disable-error-code="empty-body, misc, override, valid-type, no-untyped-def"

from typing import Any, Generic, TypeVar

from guppylang.decorator import guppy
from guppylang.definition.custom import DefaultCallChecker, NoopCompiler
from guppylang.error import GuppyError
from guppylang.module import GuppyModule
from guppylang.prelude._internal.checker import (
    ArrayLenChecker,
    CallableChecker,
    CoercingChecker,
    DunderChecker,
    FailingChecker,
    ResultChecker,
    ReversingChecker,
    UnsupportedChecker,
)
from guppylang.prelude._internal.compiler import (
    FloatBoolCompiler,
    FloatDivmodCompiler,
    FloatFloordivCompiler,
    FloatModCompiler,
    IntTruedivCompiler,
    NatTruedivCompiler,
)
from guppylang.prelude._internal.util import (
    array_n_t,
    custom_op,
    float_op,
    int_arg,
    int_op,
    linst_op,
    linst_t,
    list_op,
    list_t,
    logic_op,
    lvar_t,
    type_arg,
    var_t,
)
from guppylang.tys.builtin import (
    array_type_def,
    bool_type_def,
    float_type_def,
    int_type_def,
    linst_type_def,
    list_type_def,
    nat_type_def,
)

builtins = GuppyModule("builtins", import_builtins=False)

T = guppy.type_var(builtins, "T")
L = guppy.type_var(builtins, "L", linear=True)


def py(*_args: Any) -> Any:
    """Function to tag compile-time evaluated Python expressions in a Guppy context.

    This function throws an error when execute in a Python context. It is only intended
    to be used inside Guppy functions.
    """
    raise GuppyError("`py` can only by used in a Guppy context")


class nat:
    """Class to import in order to use nats."""


_T = TypeVar("_T")
_n = TypeVar("_n")


class array(Generic[_T, _n]):
    """Class to import in order to use arrays."""


@guppy.extend_type(builtins, bool_type_def)
class Bool:
    @guppy.hugr_op(builtins, logic_op("And", 2))
    def __and__(self: bool, other: bool) -> bool: ...

    @guppy.custom(builtins, NoopCompiler())
    def __bool__(self: bool) -> bool: ...

    @guppy.hugr_op(builtins, int_op("ifrombool", [bool], [int], n_vars=0))
    def __int__(self: bool) -> int: ...

    @guppy.hugr_op(
        builtins, custom_op("ifrombool", [bool], [nat], args=[int_arg()])
    )  # TODO: Widen to INT_WIDTH
    def __nat__(self: bool) -> nat: ...

    @guppy.custom(builtins, checker=DunderChecker("__bool__"), higher_order_value=False)
    def __new__(x): ...

    @guppy.hugr_op(builtins, logic_op("Or", 2))
    def __or__(self: bool, other: bool) -> bool: ...

    @guppy.hugr_op(builtins, logic_op("Xor", 2))
    def __xor__(self: bool, other: bool) -> bool: ...


@guppy.extend_type(builtins, nat_type_def)
class Nat:
    @guppy.custom(builtins, NoopCompiler())
    def __abs__(self: nat) -> nat: ...

    @guppy.hugr_op(builtins, int_op("iadd", [nat, nat], [nat]))
    def __add__(self: nat, other: nat) -> nat: ...

    @guppy.hugr_op(builtins, int_op("iand", [nat, nat], [nat]))
    def __and__(self: nat, other: nat) -> nat: ...

    @guppy.hugr_op(
        builtins, custom_op("itobool", [nat], [bool], args=[])
    )  # TODO: Only works with width 1 ints
    def __bool__(self: nat) -> bool: ...

    @guppy.custom(builtins, NoopCompiler())
    def __ceil__(self: nat) -> nat: ...

    @guppy.hugr_op(builtins, int_op("idivmod_u", [nat, nat], [nat, nat], n_vars=2))
    def __divmod__(self: nat, other: nat) -> tuple[nat, nat]: ...

    @guppy.hugr_op(builtins, int_op("ieq", [nat, nat], [bool]))
    def __eq__(self: nat, other: nat) -> bool: ...

    @guppy.hugr_op(
        builtins, int_op("convert_u", [nat], [float], "arithmetic.conversions")
    )
    def __float__(self: nat) -> float: ...

    @guppy.custom(builtins, NoopCompiler())
    def __floor__(self: nat) -> nat: ...

    @guppy.hugr_op(builtins, int_op("idiv_u", [nat, nat], [nat], n_vars=2))
    def __floordiv__(self: nat, other: nat) -> nat: ...

    @guppy.hugr_op(builtins, int_op("ige_u", [nat, nat], [bool]))
    def __ge__(self: nat, other: nat) -> bool: ...

    @guppy.hugr_op(builtins, int_op("igt_u", [nat, nat], [bool]))
    def __gt__(self: nat, other: nat) -> bool: ...

    @guppy.hugr_op(
        builtins, custom_op("iu_to_s", [nat], [int], args=[int_arg()])
    )  # TODO
    def __int__(self: nat) -> int: ...

    @guppy.hugr_op(builtins, int_op("inot", [nat], [nat]))
    def __invert__(self: nat) -> nat: ...

    @guppy.hugr_op(builtins, int_op("ile_u", [nat, nat], [bool]))
    def __le__(self: nat, other: nat) -> bool: ...

    @guppy.hugr_op(builtins, int_op("ishl", [nat, nat], [nat], n_vars=2))
    def __lshift__(self: nat, other: nat) -> nat: ...

    @guppy.hugr_op(builtins, int_op("ilt_u", [nat, nat], [bool]))
    def __lt__(self: nat, other: nat) -> bool: ...

    @guppy.hugr_op(builtins, int_op("imod_u", [nat, nat], [nat], n_vars=2))
    def __mod__(self: nat, other: nat) -> int: ...

    @guppy.hugr_op(builtins, int_op("imul", [nat, nat], [nat]))
    def __mul__(self: nat, other: nat) -> nat: ...

    @guppy.custom(builtins, NoopCompiler())
    def __nat__(self: nat) -> nat: ...

    @guppy.hugr_op(builtins, int_op("ine", [nat, nat], [bool]))
    def __ne__(self: nat, other: nat) -> bool: ...

    @guppy.custom(builtins, checker=DunderChecker("__nat__"), higher_order_value=False)
    def __new__(x): ...

    @guppy.hugr_op(builtins, int_op("ior", [nat, nat], [nat]))
    def __or__(self: nat, other: nat) -> nat: ...

    @guppy.custom(builtins, NoopCompiler())
    def __pos__(self: nat) -> nat: ...

    @guppy.hugr_op(
        builtins, custom_op("ipow", [nat, nat], [nat], args=[int_arg()])
    )  # TODO
    def __pow__(self: nat, other: nat) -> nat: ...

    @guppy.hugr_op(builtins, int_op("iadd", [nat, nat], [nat]), ReversingChecker())
    def __radd__(self: nat, other: nat) -> nat: ...

    @guppy.hugr_op(builtins, int_op("rand", [nat, nat], [nat]), ReversingChecker())
    def __rand__(self: nat, other: nat) -> nat: ...

    @guppy.hugr_op(
        builtins,
        int_op("idivmod_u", [nat, nat], [nat, nat], n_vars=2),
        ReversingChecker(),
    )
    def __rdivmod__(self: nat, other: nat) -> tuple[nat, nat]: ...

    @guppy.hugr_op(
        builtins, int_op("idiv_u", [nat, nat], [nat], n_vars=2), ReversingChecker()
    )
    def __rfloordiv__(self: nat, other: nat) -> nat: ...

    @guppy.hugr_op(
        builtins, int_op("ishl", [nat, nat], [nat], n_vars=2), ReversingChecker()
    )
    def __rlshift__(self: nat, other: nat) -> nat: ...

    @guppy.hugr_op(
        builtins, int_op("imod_u", [nat, nat], [nat], n_vars=2), ReversingChecker()
    )
    def __rmod__(self: nat, other: nat) -> nat: ...

    @guppy.hugr_op(builtins, int_op("imul", [nat, nat], [nat]), ReversingChecker())
    def __rmul__(self: nat, other: nat) -> nat: ...

    @guppy.hugr_op(builtins, int_op("ior", [nat, nat], [nat]), ReversingChecker())
    def __ror__(self: nat, other: nat) -> nat: ...

    @guppy.custom(builtins, NoopCompiler())
    def __round__(self: nat) -> nat: ...

    @guppy.hugr_op(
        builtins,
        custom_op("ipow", [nat, nat], [nat], args=[int_arg()]),
        ReversingChecker(),
    )
    def __rpow__(self: nat, other: nat) -> nat: ...

    @guppy.hugr_op(
        builtins, int_op("ishr", [nat, nat], [nat], n_vars=2), ReversingChecker()
    )
    def __rrshift__(self: nat, other: nat) -> nat: ...

    @guppy.hugr_op(builtins, int_op("ishr", [nat, nat], [nat], n_vars=2))
    def __rshift__(self: nat, other: nat) -> nat: ...

    @guppy.hugr_op(builtins, int_op("isub", [nat, nat], [nat]), ReversingChecker())
    def __rsub__(self: nat, other: nat) -> nat: ...

    @guppy.custom(builtins, NatTruedivCompiler(), ReversingChecker())
    def __rtruediv__(self: nat, other: nat) -> float: ...

    @guppy.hugr_op(builtins, int_op("ixor", [nat, nat], [nat]), ReversingChecker())
    def __rxor__(self: nat, other: nat) -> nat: ...

    @guppy.hugr_op(builtins, int_op("isub", [nat, nat], [nat]))
    def __sub__(self: nat, other: nat) -> nat: ...

    @guppy.custom(builtins, NatTruedivCompiler())
    def __truediv__(self: nat, other: nat) -> float: ...

    @guppy.custom(builtins, NoopCompiler())
    def __trunc__(self: nat) -> nat: ...

    @guppy.hugr_op(builtins, int_op("ixor", [nat, nat], [nat]))
    def __xor__(self: nat, other: nat) -> nat: ...


@guppy.extend_type(builtins, int_type_def)
class Int:
    @guppy.hugr_op(
        builtins, int_op("iabs", [int], [int])
    )  # TODO: Maybe wrong? (signed vs unsigned!)
    def __abs__(self: int) -> int: ...

    @guppy.hugr_op(builtins, int_op("iadd", [int, int], [int]))
    def __add__(self: int, other: int) -> int: ...

    @guppy.hugr_op(builtins, int_op("iand", [int, int], [int]))
    def __and__(self: int, other: int) -> int: ...

    @guppy.hugr_op(builtins, int_op("itobool", [int], [bool], n_vars=0))
    def __bool__(self: int) -> bool: ...

    @guppy.custom(builtins, NoopCompiler())
    def __ceil__(self: int) -> int: ...

    @guppy.hugr_op(builtins, int_op("idivmod_s", [int, int], [int, int], n_vars=2))
    def __divmod__(self: int, other: int) -> tuple[int, int]: ...

    @guppy.hugr_op(builtins, int_op("ieq", [int, int], [bool]))
    def __eq__(self: int, other: int) -> bool: ...

    @guppy.hugr_op(
        builtins, int_op("convert_s", [int], [float], "arithmetic.conversions")
    )
    def __float__(self: int) -> float: ...

    @guppy.custom(builtins, NoopCompiler())
    def __floor__(self: int) -> int: ...

    @guppy.hugr_op(builtins, int_op("idiv_s", [int, int], [int], n_vars=2))
    def __floordiv__(self: int, other: int) -> int: ...

    @guppy.hugr_op(builtins, int_op("ige_s", [int, int], [bool]))
    def __ge__(self: int, other: int) -> bool: ...

    @guppy.hugr_op(builtins, int_op("igt_s", [int, int], [bool]))
    def __gt__(self: int, other: int) -> bool: ...

    @guppy.custom(builtins, NoopCompiler())
    def __int__(self: int) -> int: ...

    @guppy.hugr_op(builtins, int_op("inot", [int], [int]))
    def __invert__(self: int) -> int: ...

    @guppy.hugr_op(builtins, int_op("ile_s", [int, int], [bool]))
    def __le__(self: int, other: int) -> bool: ...

    @guppy.hugr_op(
        builtins, int_op("ishl", [int, int], [int], n_vars=2)
    )  # TODO: RHS is unsigned
    def __lshift__(self: int, other: int) -> int: ...

    @guppy.hugr_op(builtins, int_op("ilt_s", [int, int], [bool]))
    def __lt__(self: int, other: int) -> bool: ...

    @guppy.hugr_op(builtins, int_op("imod_s", [int, int], [int], n_vars=2))
    def __mod__(self: int, other: int) -> int: ...

    @guppy.hugr_op(builtins, int_op("imul", [int, int], [int]))
    def __mul__(self: int, other: int) -> int: ...

    @guppy.hugr_op(
        builtins, custom_op("is_to_u", [int], [nat], args=[int_arg()])
    )  # TODO
    def __nat__(self: int) -> nat: ...

    @guppy.hugr_op(builtins, int_op("ine", [int, int], [bool]))
    def __ne__(self: int, other: int) -> bool: ...

    @guppy.hugr_op(builtins, int_op("ineg", [int], [int]))
    def __neg__(self: int) -> int: ...

    @guppy.custom(builtins, checker=DunderChecker("__int__"), higher_order_value=False)
    def __new__(x): ...

    @guppy.hugr_op(builtins, int_op("ior", [int, int], [int]))
    def __or__(self: int, other: int) -> int: ...

    @guppy.custom(builtins, NoopCompiler())
    def __pos__(self: int) -> int: ...

    @guppy.hugr_op(
        builtins, custom_op("ipow", [int, int], [int], args=[int_arg()])
    )  # TODO
    def __pow__(self: int, other: int) -> int: ...

    @guppy.hugr_op(builtins, int_op("iadd", [int, int], [int]), ReversingChecker())
    def __radd__(self: int, other: int) -> int: ...

    @guppy.hugr_op(builtins, int_op("rand", [int, int], [int]), ReversingChecker())
    def __rand__(self: int, other: int) -> int: ...

    @guppy.hugr_op(
        builtins,
        int_op("idivmod_s", [int, int], [int, int], n_vars=2),
        ReversingChecker(),
    )
    def __rdivmod__(self: int, other: int) -> tuple[int, int]: ...

    @guppy.hugr_op(
        builtins, int_op("idiv_s", [int, int], [int], n_vars=2), ReversingChecker()
    )
    def __rfloordiv__(self: int, other: int) -> int: ...

    @guppy.hugr_op(
        builtins, int_op("ishl", [int, int], [int], n_vars=2), ReversingChecker()
    )  # TODO: RHS is unsigned
    def __rlshift__(self: int, other: int) -> int: ...

    @guppy.hugr_op(
        builtins, int_op("imod_s", [int, int], [int], n_vars=2), ReversingChecker()
    )
    def __rmod__(self: int, other: int) -> int: ...

    @guppy.hugr_op(builtins, int_op("imul", [int, int], [int]), ReversingChecker())
    def __rmul__(self: int, other: int) -> int: ...

    @guppy.hugr_op(builtins, int_op("ior", [int, int], [int]), ReversingChecker())
    def __ror__(self: int, other: int) -> int: ...

    @guppy.custom(builtins, NoopCompiler())
    def __round__(self: int) -> int: ...

    @guppy.hugr_op(
        builtins,
        custom_op("ipow", [int, int], [int], args=[int_arg()]),
        ReversingChecker(),
    )
    def __rpow__(self: int, other: int) -> int: ...

    @guppy.hugr_op(
        builtins, int_op("ishr", [int, int], [int], n_vars=2), ReversingChecker()
    )  # TODO: RHS is unsigned
    def __rrshift__(self: int, other: int) -> int: ...

    @guppy.hugr_op(
        builtins, int_op("ishr", [int, int], [int], n_vars=2)
    )  # TODO: RHS is unsigned
    def __rshift__(self: int, other: int) -> int: ...

    @guppy.hugr_op(builtins, int_op("isub", [int, int], [int]), ReversingChecker())
    def __rsub__(self: int, other: int) -> int: ...

    @guppy.custom(builtins, IntTruedivCompiler(), ReversingChecker())
    def __rtruediv__(self: int, other: int) -> float: ...

    @guppy.hugr_op(builtins, int_op("ixor", [int, int], [int]), ReversingChecker())
    def __rxor__(self: int, other: int) -> int: ...

    @guppy.hugr_op(builtins, int_op("isub", [int, int], [int]))
    def __sub__(self: int, other: int) -> int: ...

    @guppy.custom(builtins, IntTruedivCompiler())
    def __truediv__(self: int, other: int) -> float: ...

    @guppy.custom(builtins, NoopCompiler())
    def __trunc__(self: int) -> int: ...

    @guppy.hugr_op(builtins, int_op("ixor", [int, int], [int]))
    def __xor__(self: int, other: int) -> int: ...


@guppy.extend_type(builtins, float_type_def)
class Float:
    @guppy.hugr_op(builtins, float_op("fabs", [float], [float]), CoercingChecker())
    def __abs__(self: float) -> float: ...

    @guppy.hugr_op(
        builtins, float_op("fadd", [float, float], [float]), CoercingChecker()
    )
    def __add__(self: float, other: float) -> float: ...

    @guppy.custom(builtins, FloatBoolCompiler(), CoercingChecker())
    def __bool__(self: float) -> bool: ...

    @guppy.hugr_op(builtins, float_op("fceil", [float], [float]), CoercingChecker())
    def __ceil__(self: float) -> float: ...

    @guppy.custom(builtins, FloatDivmodCompiler(), CoercingChecker())
    def __divmod__(self: float, other: float) -> tuple[float, float]: ...

    @guppy.hugr_op(builtins, float_op("feq", [float, float], [bool]), CoercingChecker())
    def __eq__(self: float, other: float) -> bool: ...

    @guppy.custom(builtins, NoopCompiler(), CoercingChecker())
    def __float__(self: float) -> float: ...

    @guppy.hugr_op(builtins, float_op("ffloor", [float], [float]), CoercingChecker())
    def __floor__(self: float) -> float: ...

    @guppy.custom(builtins, FloatFloordivCompiler(), CoercingChecker())
    def __floordiv__(self: float, other: float) -> float: ...

    @guppy.hugr_op(builtins, float_op("fge", [float, float], [bool]), CoercingChecker())
    def __ge__(self: float, other: float) -> bool: ...

    @guppy.hugr_op(builtins, float_op("fgt", [float, float], [bool]), CoercingChecker())
    def __gt__(self: float, other: float) -> bool: ...

    @guppy.hugr_op(
        builtins,
        float_op("trunc_s", [float], [int], "arithmetic.conversions"),
        CoercingChecker(),
    )
    def __int__(self: float) -> int: ...

    @guppy.hugr_op(builtins, float_op("fle", [float, float], [bool]), CoercingChecker())
    def __le__(self: float, other: float) -> bool: ...

    @guppy.hugr_op(builtins, float_op("flt", [float, float], [bool]), CoercingChecker())
    def __lt__(self: float, other: float) -> bool: ...

    @guppy.custom(builtins, FloatModCompiler(), CoercingChecker())
    def __mod__(self: float, other: float) -> float: ...

    @guppy.hugr_op(
        builtins, float_op("fmul", [float, float], [float]), CoercingChecker()
    )
    def __mul__(self: float, other: float) -> float: ...

    @guppy.hugr_op(
        builtins, float_op("trunc_u", [float], [nat], "arithmetic.conversions")
    )
    def __nat__(self: float) -> nat: ...

    @guppy.hugr_op(builtins, float_op("fne", [float, float], [bool]), CoercingChecker())
    def __ne__(self: float, other: float) -> bool: ...

    @guppy.hugr_op(builtins, float_op("fneg", [float], [float]), CoercingChecker())
    def __neg__(self: float) -> float: ...

    @guppy.custom(
        builtins, checker=DunderChecker("__float__"), higher_order_value=False
    )
    def __new__(x): ...

    @guppy.custom(builtins, NoopCompiler(), CoercingChecker())
    def __pos__(self: float) -> float: ...

    @guppy.hugr_op(
        builtins, float_op("fpow", [float, float], [float], ext="guppylang.unsupported")
    )  # TODO
    def __pow__(self: float, other: float) -> float: ...

    @guppy.hugr_op(
        builtins,
        float_op("fadd", [float, float], [float]),
        ReversingChecker(CoercingChecker()),
    )
    def __radd__(self: float, other: float) -> float: ...

    @guppy.custom(builtins, FloatDivmodCompiler(), ReversingChecker(CoercingChecker()))
    def __rdivmod__(self: float, other: float) -> tuple[float, float]: ...

    @guppy.custom(
        builtins, FloatFloordivCompiler(), ReversingChecker(CoercingChecker())
    )
    def __rfloordiv__(self: float, other: float) -> float: ...

    @guppy.custom(builtins, FloatModCompiler(), ReversingChecker(CoercingChecker()))
    def __rmod__(self: float, other: float) -> float: ...

    @guppy.hugr_op(
        builtins,
        float_op("fmul", [float, float], [float]),
        ReversingChecker(CoercingChecker()),
    )
    def __rmul__(self: float, other: float) -> float: ...

    @guppy.hugr_op(
        builtins, float_op("fround", [float], [float], ext="guppylang.unsupported")
    )  # TODO
    def __round__(self: float) -> float: ...

    @guppy.hugr_op(
        builtins,
        float_op("fpow", [float, float], [float], ext="guppylang.unsupported"),
        ReversingChecker(DefaultCallChecker()),
    )  # TODO
    def __rpow__(self: float, other: float) -> float: ...

    @guppy.hugr_op(
        builtins,
        float_op("fsub", [float, float], [float]),
        ReversingChecker(CoercingChecker()),
    )
    def __rsub__(self: float, other: float) -> float: ...

    @guppy.hugr_op(
        builtins,
        float_op("fdiv", [float, float], [float]),
        ReversingChecker(CoercingChecker()),
    )
    def __rtruediv__(self: float, other: float) -> float: ...

    @guppy.hugr_op(
        builtins, float_op("fsub", [float, float], [float]), CoercingChecker()
    )
    def __sub__(self: float, other: float) -> float: ...

    @guppy.hugr_op(
        builtins, float_op("fdiv", [float, float], [float]), CoercingChecker()
    )
    def __truediv__(self: float, other: float) -> float: ...

    @guppy.hugr_op(
        builtins,
        float_op("trunc_s", [float], [float], "arithmetic.conversions"),
        CoercingChecker(),
    )
    def __trunc__(self: float) -> float: ...


@guppy.extend_type(builtins, list_type_def)
class List:
    @guppy.hugr_op(
        builtins,
        list_op("Concat", [list_t(), list_t()], [list_t()]),
    )
    def __add__(self: list[T], other: list[T]) -> list[T]: ...

    @guppy.hugr_op(builtins, list_op("IsEmpty", [list_t()], [bool]))
    def __bool__(self: list[T]) -> bool: ...

    @guppy.hugr_op(builtins, list_op("Contains", [list_t(), var_t()], [bool]))
    def __contains__(self: list[T], el: T) -> bool: ...

    @guppy.hugr_op(builtins, list_op("AssertEmpty", [list_t()], []))
    def __end__(self: list[T]) -> None: ...

    @guppy.hugr_op(builtins, list_op("Lookup", [list_t(), int], [var_t()]))
    def __getitem__(self: list[T], idx: int) -> T: ...

    @guppy.hugr_op(
        builtins,
        list_op("IsNonEmpty", [list_t()], [bool, list_t()]),
    )
    def __hasnext__(self: list[T]) -> tuple[bool, list[T]]: ...

    @guppy.custom(builtins, NoopCompiler())
    def __iter__(self: list[T]) -> list[T]: ...

    @guppy.hugr_op(builtins, list_op("Length", [list_t()], [int]))
    def __len__(self: list[T]) -> int: ...

    @guppy.hugr_op(builtins, list_op("Repeat", [list_t(), int], [list_t()]))
    def __mul__(self: list[T], other: int) -> list[T]: ...

    @guppy.hugr_op(builtins, list_op("Pop", [list_t()], [var_t(), list_t()]))
    def __next__(self: list[T]) -> tuple[T, list[T]]: ...

    @guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
    def __new__(x): ...

    @guppy.custom(builtins, checker=FailingChecker("Guppy lists are immutable"))
    def __setitem__(self: list[T], idx: int, value: T) -> None: ...

    @guppy.hugr_op(
        builtins,
        list_op("Append", [list_t(), list_t()], [list_t()]),
        ReversingChecker(),
    )
    def __radd__(self: list[T], other: list[T]) -> list[T]: ...

    @guppy.hugr_op(builtins, list_op("Repeat", [list_t(), int], [list_t()]))
    def __rmul__(self: list[T], other: int) -> list[T]: ...

    @guppy.custom(builtins, checker=FailingChecker("Guppy lists are immutable"))
    def append(self: list[T], elt: T) -> None: ...

    @guppy.custom(builtins, checker=FailingChecker("Guppy lists are immutable"))
    def clear(self: list[T]) -> None: ...

    @guppy.custom(builtins, NoopCompiler())  # Can be noop since lists are immutable
    def copy(self: list[T]) -> list[T]: ...

    @guppy.hugr_op(builtins, list_op("Count", [list_t(), var_t()], [int]))
    def count(self: list[T], elt: T) -> int: ...

    @guppy.custom(builtins, checker=FailingChecker("Guppy lists are immutable"))
    def extend(self: list[T], seq: None) -> None: ...

    @guppy.hugr_op(builtins, list_op("Find", [list_t(), var_t()], [int]))
    def index(self: list[T], elt: T) -> int: ...

    @guppy.custom(builtins, checker=FailingChecker("Guppy lists are immutable"))
    def pop(self: list[T], idx: int) -> None: ...

    @guppy.custom(builtins, checker=FailingChecker("Guppy lists are immutable"))
    def remove(self: list[T], elt: T) -> None: ...

    @guppy.custom(builtins, checker=FailingChecker("Guppy lists are immutable"))
    def reverse(self: list[T]) -> None: ...

    @guppy.custom(builtins, checker=FailingChecker("Guppy lists are immutable"))
    def sort(self: list[T]) -> None: ...


linst = list


@guppy.extend_type(builtins, linst_type_def)
class Linst:
    @guppy.hugr_op(
        builtins,
        linst_op("Append", [linst_t(), linst_t()], [linst_t()]),
    )
    def __add__(self: linst[L], other: linst[L]) -> linst[L]: ...

    @guppy.hugr_op(builtins, linst_op("AssertEmpty", [linst_t()], []))
    def __end__(self: linst[L]) -> None: ...

    @guppy.hugr_op(
        builtins,
        linst_op("IsNonempty", [linst_t()], [bool, linst_t()]),
    )
    def __hasnext__(self: linst[L]) -> tuple[bool, linst[L]]: ...

    @guppy.custom(builtins, NoopCompiler())
    def __iter__(self: linst[L]) -> linst[L]: ...

    @guppy.hugr_op(builtins, linst_op("Length", [linst_t()], [int, linst_t()]))
    def __len__(self: linst[L]) -> tuple[int, linst[L]]: ...

    @guppy.hugr_op(
        builtins,
        linst_op("Pop", [linst_t()], [lvar_t(), linst_t()]),
    )
    def __next__(self: linst[L]) -> tuple[L, linst[L]]: ...

    @guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
    def __new__(x): ...

    @guppy.hugr_op(
        builtins,
        linst_op("Append", [linst_t(), linst_t()], [linst_t()]),
        ReversingChecker(),
    )
    def __radd__(self: linst[L], other: linst[L]) -> linst[L]: ...

    @guppy.hugr_op(builtins, linst_op("Repeat", [linst_t(), int], [linst_t()]))
    def __rmul__(self: linst[L], other: int) -> linst[L]: ...

    @guppy.hugr_op(
        builtins,
        linst_op("Push", [linst_t(), lvar_t()], [linst_t()]),
    )
    def append(self: linst[L], elt: L) -> linst[L]: ...

    @guppy.hugr_op(
        builtins,
        linst_op("PopAt", [linst_t(), int], [lvar_t(), linst_t()]),
    )
    def pop(self: linst[L], idx: int) -> tuple[L, linst[L]]: ...

    @guppy.hugr_op(builtins, linst_op("Reverse", [linst_t()], [linst_t()]))
    def reverse(self: linst[L]) -> linst[L]: ...

    @guppy.custom(builtins, checker=FailingChecker("Guppy lists are immutable"))
    def sort(self: linst[T]) -> None: ...


n = guppy.nat_var(builtins, "n")


@guppy.extend_type(builtins, array_type_def)
class Array:
    @guppy.hugr_op(
        builtins,
        custom_op(
            "ArrayGet",
            [array_n_t(), int],
            [var_t(1)],
            args=[int_arg(), type_arg()],
            variable_remap={0: 1, 1: 0},
        ),
    )
    def __getitem__(self: array[T, n], idx: int) -> T: ...

    @guppy.custom(builtins, checker=ArrayLenChecker())
    def __len__(self: array[T, n]) -> int: ...


# TODO: This is a temporary hack until we have implemented the proper results mechanism.
@guppy.custom(builtins, checker=ResultChecker(), higher_order_value=False)
def result(tag, value): ...


@guppy.custom(builtins, checker=DunderChecker("__abs__"), higher_order_value=False)
def abs(x): ...


@guppy.custom(builtins, checker=CallableChecker(), higher_order_value=False)
def callable(x): ...


@guppy.custom(
    builtins, checker=DunderChecker("__divmod__", num_args=2), higher_order_value=False
)
def divmod(x, y): ...


@guppy.custom(builtins, checker=DunderChecker("__len__"), higher_order_value=False)
def len(x): ...


@guppy.custom(
    builtins, checker=DunderChecker("__pow__", num_args=2), higher_order_value=False
)
def pow(x, y): ...


@guppy.custom(builtins, checker=DunderChecker("__round__"), higher_order_value=False)
def round(x): ...


# Python builtins that are not supported yet:


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def aiter(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def all(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def anext(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def any(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def bin(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def breakpoint(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def bytearray(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def bytes(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def chr(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def classmethod(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def compile(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def complex(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def delattr(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def dict(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def dir(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def enumerate(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def eval(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def exec(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def filter(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def format(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def forozenset(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def getattr(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def globals(): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def hasattr(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def hash(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def help(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def hex(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def id(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def input(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def isinstance(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def issubclass(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def iter(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def locals(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def map(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def max(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def memoryview(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def min(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def next(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def object(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def oct(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def open(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def ord(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def print(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def property(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def range(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def repr(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def reversed(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def set(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def setattr(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def slice(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def sorted(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def staticmethod(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def str(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def sum(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def super(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def type(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def vars(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def zip(x): ...


@guppy.custom(builtins, checker=UnsupportedChecker(), higher_order_value=False)
def __import__(x): ...
