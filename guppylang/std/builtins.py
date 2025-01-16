"""Guppy module for builtin types and operations."""

# mypy: disable-error-code="empty-body, misc, override, valid-type, no-untyped-def"

from typing import Any, Generic, TypeVar, no_type_check

import hugr.std.int

from guppylang.decorator import guppy
from guppylang.definition.custom import NoopCompiler
from guppylang.std._internal.checker import (
    ArrayLenChecker,
    CallableChecker,
    DunderChecker,
    NewArrayChecker,
    PanicChecker,
    RangeChecker,
    ResultChecker,
    ReversingChecker,
    UnsupportedChecker,
)
from guppylang.std._internal.compiler.array import (
    ArrayGetitemCompiler,
    ArrayIterEndCompiler,
    ArraySetitemCompiler,
    NewArrayCompiler,
)
from guppylang.std._internal.compiler.list import (
    ListGetitemCompiler,
    ListLengthCompiler,
    ListPopCompiler,
    ListPushCompiler,
    ListSetitemCompiler,
)
from guppylang.std._internal.compiler.prelude import MemSwapCompiler
from guppylang.std._internal.util import (
    float_op,
    int_op,
    logic_op,
    unsupported_op,
)
from guppylang.tys.builtin import (
    array_type_def,
    bool_type_def,
    float_type_def,
    int_type_def,
    list_type_def,
    nat_type_def,
    sized_iter_type_def,
    string_type_def,
)

guppy.init_module(import_builtins=False)

T = guppy.type_var("T")
L = guppy.type_var("L", copyable=False, droppable=False)


def py(*args: Any) -> Any:
    """Function to tag compile-time evaluated Python expressions in a Guppy context.

    This function acts like the identity when execute in a Python context.
    """
    return tuple(args)


class _Owned:
    """Dummy class to support `@owned` annotations."""

    def __rmatmul__(self, other: Any) -> Any:
        return other


owned = _Owned()


class nat:
    """Class to import in order to use nats."""


_T = TypeVar("_T")
_n = TypeVar("_n")


class array(Generic[_T, _n]):
    """Class to import in order to use arrays."""

    def __init__(self, *args: Any):
        pass


@guppy.extend_type(bool_type_def)
class Bool:
    @guppy.hugr_op(logic_op("And"))
    def __and__(self: bool, other: bool) -> bool: ...

    @guppy.custom(NoopCompiler())
    def __bool__(self: bool) -> bool: ...

    @guppy.hugr_op(logic_op("Eq"))
    def __eq__(self: bool, other: bool) -> bool: ...

    @guppy
    @no_type_check
    def __ne__(self: bool, other: bool) -> bool:
        return not self == other

    @guppy
    @no_type_check
    def __int__(self: bool) -> int:
        return 1 if self else 0

    @guppy
    @no_type_check
    def __nat__(self: bool) -> nat:
        # TODO: Type information doesn't flow through the `if` expression, so we
        #  have to insert the `nat` coercions by hand.
        #  See https://github.com/CQCL/guppylang/issues/707
        return nat(1) if self else nat(0)

    @guppy.custom(checker=DunderChecker("__bool__"), higher_order_value=False)
    def __new__(x): ...

    @guppy.hugr_op(logic_op("Or"))
    def __or__(self: bool, other: bool) -> bool: ...

    # TODO: Use hugr op once implemented: https://github.com/CQCL/hugr/issues/1418
    @guppy
    def __xor__(self: bool, other: bool) -> bool:
        return self != other


@guppy.extend_type(string_type_def)
class String:
    @guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
    def __new__(x): ...


@guppy.extend_type(nat_type_def)
class Nat:
    @guppy.custom(NoopCompiler())
    def __abs__(self: nat) -> nat: ...

    @guppy.hugr_op(int_op("iadd"))
    def __add__(self: nat, other: nat) -> nat: ...

    @guppy.hugr_op(int_op("iand"))
    def __and__(self: nat, other: nat) -> nat: ...

    @guppy
    @no_type_check
    def __bool__(self: nat) -> bool:
        return self != 0

    @guppy.custom(NoopCompiler())
    def __ceil__(self: nat) -> nat: ...

    @guppy.hugr_op(int_op("idivmod_u", n_vars=2))
    def __divmod__(self: nat, other: nat) -> tuple[nat, nat]: ...

    @guppy.hugr_op(int_op("ieq"))
    def __eq__(self: nat, other: nat) -> bool: ...

    @guppy.hugr_op(int_op("convert_u", hugr.std.int.CONVERSIONS_EXTENSION))
    def __float__(self: nat) -> float: ...

    @guppy.custom(NoopCompiler())
    def __floor__(self: nat) -> nat: ...

    @guppy.hugr_op(int_op("idiv_u"))
    def __floordiv__(self: nat, other: nat) -> nat: ...

    @guppy.hugr_op(int_op("ige_u"))
    def __ge__(self: nat, other: nat) -> bool: ...

    @guppy.hugr_op(int_op("igt_u"))
    def __gt__(self: nat, other: nat) -> bool: ...

    # TODO: Use "iu_to_s" once we have lowering:
    #  https://github.com/CQCL/hugr/issues/1806
    @guppy.custom(NoopCompiler())
    def __int__(self: nat) -> int: ...

    @guppy.hugr_op(int_op("inot"))
    def __invert__(self: nat) -> nat: ...

    @guppy.hugr_op(int_op("ile_u"))
    def __le__(self: nat, other: nat) -> bool: ...

    @guppy.hugr_op(int_op("ishl", n_vars=2))
    def __lshift__(self: nat, other: nat) -> nat: ...

    @guppy.hugr_op(int_op("ilt_u"))
    def __lt__(self: nat, other: nat) -> bool: ...

    @guppy.hugr_op(int_op("imod_u", n_vars=2))
    def __mod__(self: nat, other: nat) -> int: ...

    @guppy.hugr_op(int_op("imul"))
    def __mul__(self: nat, other: nat) -> nat: ...

    @guppy.custom(NoopCompiler())
    def __nat__(self: nat) -> nat: ...

    @guppy.hugr_op(int_op("ine"))
    def __ne__(self: nat, other: nat) -> bool: ...

    @guppy.custom(checker=DunderChecker("__nat__"), higher_order_value=False)
    def __new__(x): ...

    @guppy.hugr_op(int_op("ior"))
    def __or__(self: nat, other: nat) -> nat: ...

    @guppy.custom(NoopCompiler())
    def __pos__(self: nat) -> nat: ...

    @guppy.hugr_op(int_op("ipow"))
    def __pow__(self: nat, other: nat) -> nat: ...

    @guppy.custom(checker=ReversingChecker())
    def __radd__(self: nat, other: nat) -> nat: ...

    @guppy.custom(checker=ReversingChecker())
    def __rand__(self: nat, other: nat) -> nat: ...

    @guppy.custom(checker=ReversingChecker())
    def __rdivmod__(self: nat, other: nat) -> tuple[nat, nat]: ...

    @guppy.custom(checker=ReversingChecker())
    def __rfloordiv__(self: nat, other: nat) -> nat: ...

    @guppy.custom(checker=ReversingChecker())
    def __rlshift__(self: nat, other: nat) -> nat: ...

    @guppy.custom(checker=ReversingChecker())
    def __rmod__(self: nat, other: nat) -> nat: ...

    @guppy.custom(checker=ReversingChecker())
    def __rmul__(self: nat, other: nat) -> nat: ...

    @guppy.custom(checker=ReversingChecker())
    def __ror__(self: nat, other: nat) -> nat: ...

    @guppy.custom(NoopCompiler())
    def __round__(self: nat) -> nat: ...

    @guppy.custom(checker=ReversingChecker())
    def __rpow__(self: nat, other: nat) -> nat: ...

    @guppy.custom(checker=ReversingChecker())
    def __rrshift__(self: nat, other: nat) -> nat: ...

    @guppy.hugr_op(int_op("ishr"))
    def __rshift__(self: nat, other: nat) -> nat: ...

    @guppy.custom(checker=ReversingChecker())
    def __rsub__(self: nat, other: nat) -> nat: ...

    @guppy.custom(checker=ReversingChecker())
    def __rtruediv__(self: nat, other: nat) -> float: ...

    @guppy.custom(checker=ReversingChecker())
    def __rxor__(self: nat, other: nat) -> nat: ...

    @guppy.hugr_op(int_op("isub"))
    def __sub__(self: nat, other: nat) -> nat: ...

    @guppy
    @no_type_check
    def __truediv__(self: nat, other: nat) -> float:
        return float(self) / float(other)

    @guppy.custom(NoopCompiler())
    def __trunc__(self: nat) -> nat: ...

    @guppy.hugr_op(int_op("ixor"))
    def __xor__(self: nat, other: nat) -> nat: ...


@guppy.extend_type(int_type_def)
class Int:
    @guppy.hugr_op(int_op("iabs"))  # TODO: Maybe wrong? (signed vs unsigned!)
    def __abs__(self: int) -> int: ...

    @guppy.hugr_op(int_op("iadd"))
    def __add__(self: int, other: int) -> int: ...

    @guppy.hugr_op(int_op("iand"))
    def __and__(self: int, other: int) -> int: ...

    @guppy
    @no_type_check
    def __bool__(self: int) -> bool:
        return self != 0

    @guppy.custom(NoopCompiler())
    def __ceil__(self: int) -> int: ...

    @guppy.hugr_op(int_op("idivmod_s"))
    def __divmod__(self: int, other: int) -> tuple[int, int]: ...

    @guppy.hugr_op(int_op("ieq"))
    def __eq__(self: int, other: int) -> bool: ...

    @guppy.hugr_op(int_op("convert_s", hugr.std.int.CONVERSIONS_EXTENSION))
    def __float__(self: int) -> float: ...

    @guppy.custom(NoopCompiler())
    def __floor__(self: int) -> int: ...

    @guppy.hugr_op(int_op("idiv_s"))
    def __floordiv__(self: int, other: int) -> int: ...

    @guppy.hugr_op(int_op("ige_s"))
    def __ge__(self: int, other: int) -> bool: ...

    @guppy.hugr_op(int_op("igt_s"))
    def __gt__(self: int, other: int) -> bool: ...

    @guppy.custom(NoopCompiler())
    def __int__(self: int) -> int: ...

    @guppy.hugr_op(int_op("inot"))
    def __invert__(self: int) -> int: ...

    @guppy.hugr_op(int_op("ile_s"))
    def __le__(self: int, other: int) -> bool: ...

    @guppy.hugr_op(int_op("ishl"))  # TODO: RHS is unsigned
    def __lshift__(self: int, other: int) -> int: ...

    @guppy.hugr_op(int_op("ilt_s"))
    def __lt__(self: int, other: int) -> bool: ...

    @guppy.hugr_op(int_op("imod_s"))
    def __mod__(self: int, other: int) -> int: ...

    @guppy.hugr_op(int_op("imul"))
    def __mul__(self: int, other: int) -> int: ...

    @guppy.hugr_op(int_op("is_to_u"))  # TODO
    def __nat__(self: int) -> nat: ...

    @guppy.hugr_op(int_op("ine"))
    def __ne__(self: int, other: int) -> bool: ...

    @guppy.hugr_op(int_op("ineg"))
    def __neg__(self: int) -> int: ...

    @guppy.custom(checker=DunderChecker("__int__"), higher_order_value=False)
    def __new__(x): ...

    @guppy.hugr_op(int_op("ior"))
    def __or__(self: int, other: int) -> int: ...

    @guppy.custom(NoopCompiler())
    def __pos__(self: int) -> int: ...

    # TODO use hugr int op "ipow"
    # once lowering available
    @guppy
    @no_type_check
    def __pow__(self: int, exponent: int) -> int:
        if exponent < 0:
            panic(
                "Negative exponent not supported in"
                "__pow__ with int type base. Try casting the base to float."
            )
        res = 1
        for _ in range(exponent):
            res *= self
        return res

    @guppy.custom(checker=ReversingChecker())
    def __radd__(self: int, other: int) -> int: ...

    @guppy.custom(checker=ReversingChecker())
    def __rand__(self: int, other: int) -> int: ...

    @guppy.custom(checker=ReversingChecker())
    def __rdivmod__(self: int, other: int) -> tuple[int, int]: ...

    @guppy.custom(checker=ReversingChecker())
    def __rfloordiv__(self: int, other: int) -> int: ...

    @guppy.custom(checker=ReversingChecker())  # TODO: RHS is unsigned
    def __rlshift__(self: int, other: int) -> int: ...

    @guppy.custom(checker=ReversingChecker())
    def __rmod__(self: int, other: int) -> int: ...

    @guppy.custom(checker=ReversingChecker())
    def __rmul__(self: int, other: int) -> int: ...

    @guppy.custom(checker=ReversingChecker())
    def __ror__(self: int, other: int) -> int: ...

    @guppy.custom(NoopCompiler())
    def __round__(self: int) -> int: ...

    @guppy.custom(checker=ReversingChecker())
    def __rpow__(self: int, other: int) -> int: ...

    @guppy.custom(checker=ReversingChecker())  # TODO: RHS is unsigned
    def __rrshift__(self: int, other: int) -> int: ...

    @guppy.custom(checker=ReversingChecker())  # TODO: RHS is unsigned
    def __rshift__(self: int, other: int) -> int: ...

    @guppy.custom(checker=ReversingChecker())
    def __rsub__(self: int, other: int) -> int: ...

    @guppy.custom(checker=ReversingChecker())
    def __rtruediv__(self: int, other: int) -> float: ...

    @guppy.custom(checker=ReversingChecker())
    def __rxor__(self: int, other: int) -> int: ...

    @guppy.hugr_op(int_op("isub"))
    def __sub__(self: int, other: int) -> int: ...

    @guppy
    @no_type_check
    def __truediv__(self: int, other: int) -> float:
        return float(self) / float(other)

    @guppy.custom(NoopCompiler())
    def __trunc__(self: int) -> int: ...

    @guppy.hugr_op(int_op("ixor"))
    def __xor__(self: int, other: int) -> int: ...


@guppy.extend_type(float_type_def)
class Float:
    @guppy.hugr_op(float_op("fabs"))
    def __abs__(self: float) -> float: ...

    @guppy.hugr_op(float_op("fadd"))
    def __add__(self: float, other: float) -> float: ...

    @guppy
    @no_type_check
    def __bool__(self: float) -> bool:
        return self != 0.0

    @guppy.hugr_op(float_op("fceil"))
    def __ceil__(self: float) -> float: ...

    @guppy
    @no_type_check
    def __divmod__(self: float, other: float) -> tuple[float, float]:
        return self // other, self.__mod__(other)

    @guppy.hugr_op(float_op("feq"))
    def __eq__(self: float, other: float) -> bool: ...

    @guppy.custom(NoopCompiler())
    def __float__(self: float) -> float: ...

    @guppy.hugr_op(float_op("ffloor"))
    def __floor__(self: float) -> float: ...

    @guppy
    @no_type_check
    def __floordiv__(self: float, other: float) -> float:
        return (self / other).__floor__()

    @guppy.hugr_op(float_op("fge"))
    def __ge__(self: float, other: float) -> bool: ...

    @guppy.hugr_op(float_op("fgt"))
    def __gt__(self: float, other: float) -> bool: ...

    @guppy.hugr_op(unsupported_op("trunc_s"))  # TODO `trunc_s` returns an option
    def __int__(self: float) -> int: ...

    @guppy.hugr_op(float_op("fle"))
    def __le__(self: float, other: float) -> bool: ...

    @guppy.hugr_op(float_op("flt"))
    def __lt__(self: float, other: float) -> bool: ...

    @guppy
    @no_type_check
    def __mod__(self: float, other: float) -> float:
        return self - (self // other) * other

    @guppy.hugr_op(float_op("fmul"))
    def __mul__(self: float, other: float) -> float: ...

    @guppy.hugr_op(unsupported_op("trunc_u"))  # TODO `trunc_u` returns an option
    def __nat__(self: float) -> nat: ...

    @guppy.hugr_op(float_op("fne"))
    def __ne__(self: float, other: float) -> bool: ...

    @guppy.hugr_op(float_op("fneg"))
    def __neg__(self: float) -> float: ...

    @guppy.custom(checker=DunderChecker("__float__"), higher_order_value=False)
    def __new__(x): ...

    @guppy.custom(NoopCompiler())
    def __pos__(self: float) -> float: ...

    @guppy.hugr_op(float_op("fpow"))  # TODO
    def __pow__(self: float, other: float) -> float: ...

    @guppy.custom(checker=ReversingChecker())
    def __radd__(self: float, other: float) -> float: ...

    @guppy.custom(checker=ReversingChecker())
    def __rdivmod__(self: float, other: float) -> tuple[float, float]: ...

    @guppy.custom(checker=ReversingChecker())
    def __rfloordiv__(self: float, other: float) -> float: ...

    @guppy.custom(checker=ReversingChecker())
    def __rmod__(self: float, other: float) -> float: ...

    @guppy.custom(checker=ReversingChecker())
    def __rmul__(self: float, other: float) -> float: ...

    @guppy.hugr_op(float_op("fround"))  # TODO
    def __round__(self: float) -> float: ...

    @guppy.custom(checker=ReversingChecker())
    def __rpow__(self: float, other: float) -> float: ...

    @guppy.custom(checker=ReversingChecker())
    def __rsub__(self: float, other: float) -> float: ...

    @guppy.custom(checker=ReversingChecker())
    def __rtruediv__(self: float, other: float) -> float: ...

    @guppy.hugr_op(float_op("fsub"))
    def __sub__(self: float, other: float) -> float: ...

    @guppy.hugr_op(float_op("fdiv"))
    def __truediv__(self: float, other: float) -> float: ...

    @guppy.hugr_op(unsupported_op("trunc_s"))  # TODO `trunc_s` returns an option
    def __trunc__(self: float) -> float: ...


@guppy.extend_type(list_type_def)
class List:
    @guppy.custom(ListGetitemCompiler())
    def __getitem__(self: list[L], idx: int) -> L: ...

    @guppy.custom(ListSetitemCompiler())
    def __setitem__(self: list[L], idx: int, value: L @ owned) -> None: ...

    @guppy.custom(ListLengthCompiler())
    def __len__(self: list[L]) -> int: ...

    @guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
    def __new__(x): ...

    @guppy.custom(NoopCompiler())  # TODO: define via Guppy source instead
    def __iter__(self: list[L] @ owned) -> list[L]: ...

    @guppy.hugr_op(unsupported_op("IsNotEmpty"))  # TODO
    def __hasnext__(self: list[L] @ owned) -> tuple[bool, list[L]]: ...

    @guppy.hugr_op(unsupported_op("AssertEmpty"))  # TODO
    def __end__(self: list[L] @ owned) -> None: ...

    @guppy.hugr_op(unsupported_op("pop"))
    def __next__(self: list[L] @ owned) -> tuple[L, list[L]]: ...

    @guppy.custom(ListPushCompiler())
    def append(self: list[L], item: L @ owned) -> None: ...

    @guppy.custom(ListPopCompiler())
    def pop(self: list[L]) -> L: ...


n = guppy.nat_var("n")


@guppy.extend_type(array_type_def)
class Array:
    @guppy.custom(ArrayGetitemCompiler())
    def __getitem__(self: array[L, n], idx: int) -> L: ...

    @guppy.custom(ArraySetitemCompiler())
    def __setitem__(self: array[L, n], idx: int, value: L @ owned) -> None: ...

    @guppy.custom(checker=ArrayLenChecker())
    def __len__(self: array[L, n]) -> int: ...

    @guppy.custom(NewArrayCompiler(), NewArrayChecker(), higher_order_value=False)
    def __new__(): ...

    @guppy
    @no_type_check
    def __iter__(self: array[L, n] @ owned) -> "SizedIter[ArrayIter[L, n], n]":
        return SizedIter(ArrayIter(self, 0))


@guppy.struct
class ArrayIter(Generic[L, n]):
    xs: array[L, n]
    i: int

    @guppy
    @no_type_check
    def __hasnext__(self: "ArrayIter[L, n]" @ owned) -> tuple[bool, "ArrayIter[L, n]"]:
        return self.i < int(n), self

    @guppy
    @no_type_check
    def __next__(self: "ArrayIter[L, n]" @ owned) -> tuple[L, "ArrayIter[L, n]"]:
        elem = _array_unsafe_getitem(self.xs, self.i)
        return elem, ArrayIter(self.xs, self.i + 1)

    @guppy.custom(ArrayIterEndCompiler())
    def __end__(self: "ArrayIter[L, n]" @ owned) -> None: ...


@guppy.custom(ArrayGetitemCompiler())
def _array_unsafe_getitem(xs: array[L, n], idx: int) -> L: ...


@guppy.extend_type(sized_iter_type_def)
class SizedIter:
    """A wrapper around an iterator type `L` promising that the iterator will yield
    exactly `n` values.

    Annotating an iterator with an incorrect size is undefined behaviour.
    """

    def __class_getitem__(cls, item: Any) -> type:
        # Dummy implementation to allow subscripting of the `SizedIter` type in
        # positions that are evaluated by the Python interpreter
        return cls

    @guppy.custom(NoopCompiler())
    def __new__(iterator: L @ owned) -> "SizedIter[L, n]":  # type: ignore[type-arg]
        """Casts an iterator into a `SizedIter`."""

    @guppy.custom(NoopCompiler())
    def unwrap_iter(self: "SizedIter[L, n]" @ owned) -> L:
        """Extracts the actual iterator."""

    @guppy.custom(NoopCompiler())
    def __iter__(self: "SizedIter[L, n]" @ owned) -> "SizedIter[L, n]":  # type: ignore[type-arg]
        """Dummy implementation making sized iterators iterable themselves."""


# TODO: This is a temporary hack until we have implemented the proper results mechanism.
@guppy.custom(checker=ResultChecker(), higher_order_value=False)
def result(tag, value): ...


@guppy.custom(checker=PanicChecker(), higher_order_value=False)
def panic(msg, *args):
    """Panic, throwing an error with the given message, and immediately exit the
    program.

    Return type is arbitrary, as this function never returns.

    Args:
        msg: The message to display. Must be a string literal.
        args: Arbitrary extra inputs, will not affect the message. Only useful for
        consuming linear values.
    """


@guppy.custom(checker=DunderChecker("__abs__"), higher_order_value=False)
def abs(x): ...


@guppy.custom(checker=CallableChecker(), higher_order_value=False)
def callable(x): ...


@guppy.custom(checker=DunderChecker("__divmod__", num_args=2), higher_order_value=False)
def divmod(x, y): ...


@guppy.custom(checker=DunderChecker("__len__"), higher_order_value=False)
def len(x): ...


@guppy.custom(checker=DunderChecker("__pow__", num_args=2), higher_order_value=False)
def pow(x, y): ...


@guppy.custom(checker=DunderChecker("__round__"), higher_order_value=False)
def round(x): ...


# Python builtins that are not supported yet:


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def aiter(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def all(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def anext(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def any(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def bin(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def breakpoint(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def bytearray(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def bytes(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def chr(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def classmethod(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def compile(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def complex(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def delattr(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def dict(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def dir(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def enumerate(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def eval(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def exec(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def filter(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def format(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def forozenset(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def getattr(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def globals(): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def hasattr(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def hash(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def help(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def hex(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def id(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def input(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def isinstance(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def issubclass(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def iter(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def locals(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def map(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def max(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def memoryview(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def min(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def next(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def object(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def oct(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def open(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def ord(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def print(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def property(x): ...


@guppy.struct
class Range:
    next: int
    stop: int

    @guppy
    def __iter__(self: "Range") -> "Range":
        return self

    @guppy
    def __hasnext__(self: "Range") -> tuple[bool, "Range"]:
        return (self.next < self.stop, self)

    @guppy
    def __next__(self: "Range") -> tuple[int, "Range"]:
        # Fine not to check bounds while we can only be called from inside a `for` loop.
        # if self.start >= self.stop:
        #    raise StopIteration
        return (self.next, Range(self.next + 1, self.stop))  # type: ignore[call-arg]

    @guppy
    def __end__(self: "Range") -> None:
        pass


@guppy.custom(checker=RangeChecker(), higher_order_value=False)
def range(stop: int) -> Range:
    """Limited version of python range().
    Only a single argument (stop/limit) is supported."""


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def repr(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def reversed(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def set(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def setattr(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def slice(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def sorted(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def staticmethod(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def sum(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def super(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def type(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def vars(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def zip(x): ...


@guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
def __import__(x): ...


@guppy.custom(MemSwapCompiler())
def mem_swap(x: L, y: L) -> None:
    """Swaps the values of two variables."""
