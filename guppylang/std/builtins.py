"""Guppy module for builtin types and operations."""

# ruff: noqa: E501
# mypy: disable-error-code="empty-body, misc, override, valid-type, no-untyped-def, has-type"

from __future__ import annotations

import builtins
from typing import Any, Generic, TypeVar, no_type_check

import hugr.std.int
from typing_extensions import deprecated

from guppylang.decorator import guppy
from guppylang.definition.custom import CopyInoutCompiler, NoopCompiler
from guppylang.std._internal.checker import (
    ArrayCopyChecker,
    BarrierChecker,
    CallableChecker,
    DunderChecker,
    ExitChecker,
    NewArrayChecker,
    PanicChecker,
    RangeChecker,
    ResultChecker,
    ReversingChecker,
    UnsupportedChecker,
)
from guppylang.std._internal.compiler.array import (
    ArrayGetitemCompiler,
    ArrayIterAsertAllUsedCompiler,
    ArraySetitemCompiler,
    NewArrayCompiler,
)
from guppylang.std._internal.compiler.frozenarray import FrozenarrayGetitemCompiler
from guppylang.std._internal.compiler.list import (
    ListGetitemCompiler,
    ListLengthCompiler,
    ListPopCompiler,
    ListPushCompiler,
    ListSetitemCompiler,
)
from guppylang.std._internal.compiler.prelude import (
    MemSwapCompiler,
    UnwrapOpCompiler,
)
from guppylang.std._internal.util import (
    external_op,
    float_op,
    int_op,
    logic_op,
    unsupported_op,
)
from guppylang.tys.builtin import (
    array_type_def,
    bool_type_def,
    float_type_def,
    frozenarray_type_def,
    int_type_def,
    list_type_def,
    nat_type_def,
    sized_iter_type_def,
    string_type_def,
)

guppy.init_module(import_builtins=False)

T = guppy.type_var("T")
L = guppy.type_var("L", copyable=False, droppable=False)


def comptime(*args: Any) -> Any:
    """Function to tag compile-time evaluated Python expressions in a Guppy context.

    This function acts like the identity when execute in a Python context.
    """
    return tuple(args)


#: Deprecated alias for `comptime` expressions
py = deprecated("Use `comptime` instead")(comptime)


class _Owned:
    """Dummy class to support `@owned` annotations."""

    def __rmatmul__(self, other: Any) -> Any:
        return other


owned = _Owned()


_T = TypeVar("_T")
_n = TypeVar("_n")


@guppy.extend_type(bool_type_def)
class bool:
    """Booleans representing truth values.

    The bool type has exactly two constant instances: ``True`` and ``False``.

    The bool constructor takes a single argument and converts it to ``True`` or
    ``False`` using the standard truth testing procedure.
    """

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

    @guppy.hugr_op(logic_op("Xor"))
    def __xor__(self: bool, other: bool) -> bool: ...


@guppy.extend_type(string_type_def)
class str:
    """A string, i.e. immutable sequences of Unicode code points."""

    @guppy.custom(checker=UnsupportedChecker(), higher_order_value=False)
    def __new__(x): ...


@guppy.extend_type(nat_type_def)
class nat:
    """A 64-bit unsigned integer."""

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

    @guppy.hugr_op(int_op("ishl"))
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
class int:
    """A 64-bit signed integer."""

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

    @guppy
    @no_type_check
    def __pow__(self: int, exponent: int) -> int:
        if exponent < 0:
            panic(
                "Negative exponent not supported in"
                "__pow__ with int type base. Try casting the base to float."
            )
        return self.__pow_impl(exponent)

    @guppy.hugr_op(int_op("ipow"))
    def __pow_impl(self: int, exponent: int) -> int: ...

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

    @guppy.hugr_op(int_op("ishr"))  # TODO: RHS is unsigned
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
class float:
    """An IEEE754 double-precision floating point value."""

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

    @guppy.custom(
        UnwrapOpCompiler(
            # Use `int_op` to instantiate type arg with 64-bit integer.
            int_op("trunc_s", hugr.std.int.CONVERSIONS_EXTENSION),
        )
    )
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

    @guppy.custom(
        UnwrapOpCompiler(
            # Use `int_op` to instantiate type arg with 64-bit integer.
            int_op("trunc_u", hugr.std.int.CONVERSIONS_EXTENSION),
        )
    )
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
class list(Generic[_T]):
    """Mutable sequence items with homogeneous types."""

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

    @guppy.hugr_op(unsupported_op("pop"))
    def __next__(self: list[L] @ owned) -> Option[tuple[L, list[L]]]: ...  # type: ignore[type-arg]

    @guppy.custom(ListPushCompiler())
    def append(self: list[L], item: L @ owned) -> None: ...

    @guppy.custom(ListPopCompiler())
    def pop(self: list[L]) -> L: ...


n = guppy.nat_var("n")


@guppy.extend_type(array_type_def)
class array(builtins.list[_T], Generic[_T, _n]):
    """Sequence of homogeneous values with statically known fixed length."""

    @guppy.custom(ArrayGetitemCompiler())
    def __getitem__(self: array[L, n], idx: int) -> L: ...

    @guppy.custom(ArraySetitemCompiler())
    def __setitem__(self: array[L, n], idx: int, value: L @ owned) -> None: ...

    @guppy
    @no_type_check
    def __len__(self: array[L, n]) -> int:
        return n

    @guppy.custom(NewArrayCompiler(), NewArrayChecker(), higher_order_value=False)
    def __new__(): ...

    @guppy
    @no_type_check
    def __iter__(self: array[L, n] @ owned) -> SizedIter[ArrayIter[L, n], n]:
        return SizedIter(ArrayIter(self, 0))

    @guppy.custom(CopyInoutCompiler(), ArrayCopyChecker())
    def copy(self: array[T, n]) -> array[T, n]: ...

    def __new__(cls, *args: _T) -> builtins.list[_T]:  # type: ignore[no-redef]  # noqa: F811
        # Runtime array constructor that is used for comptime. We return an actual list
        # in line with the comptime unpacking logic that turns arrays into lists.
        return [*args]


@guppy.struct
class ArrayIter(Generic[L, n]):
    """Iterator over arrays."""

    xs: array[L, n]
    i: int

    @guppy
    @no_type_check
    def __next__(
        self: ArrayIter[L, n] @ owned,
    ) -> Option[tuple[L, ArrayIter[L, n]]]:
        if self.i < int(n):
            elem = _array_unsafe_getitem(self.xs, self.i)
            return some((elem, ArrayIter(self.xs, self.i + 1)))
        self._assert_all_used()
        return nothing()

    @guppy.custom(ArrayIterAsertAllUsedCompiler())
    def _assert_all_used(self: ArrayIter[L, n] @ owned) -> None: ...


@guppy.custom(ArrayGetitemCompiler())
def _array_unsafe_getitem(xs: array[L, n], idx: int) -> L: ...


@guppy.extend_type(frozenarray_type_def)
class frozenarray(Generic[T, n]):
    """An immutable array of fixed static size."""

    @guppy.custom(FrozenarrayGetitemCompiler())
    def __getitem__(self: frozenarray[T, n], item: int) -> T: ...  # type: ignore[type-arg]

    @guppy
    @no_type_check
    def __len__(self: frozenarray[T, n]) -> int:
        return n

    @guppy
    @no_type_check
    def __iter__(self: frozenarray[T, n]) -> SizedIter[FrozenarrayIter[T, n], n]:
        return SizedIter(FrozenarrayIter(self, 0))

    @guppy
    @no_type_check
    def mutable_copy(self: frozenarray[T, n]) -> array[T, n]:
        """Creates a mutable copy of this array."""
        return array(x for x in self)


@guppy.struct
class FrozenarrayIter(Generic[T, n]):
    """Iterator for frozenarrays."""

    xs: frozenarray[T, n]  # type: ignore[type-arg]
    i: int

    @guppy
    @no_type_check
    def __next__(
        self: FrozenarrayIter[T, n],
    ) -> Option[tuple[T, FrozenarrayIter[T, n]]]:
        if self.i < int(n):
            return some((self.xs[self.i], FrozenarrayIter(self.xs, self.i + 1)))
        return nothing()


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
    def __new__(iterator: L @ owned) -> SizedIter[L, n]:  # type: ignore[type-arg]
        """Casts an iterator into a `SizedIter`."""

    @guppy.custom(NoopCompiler())
    def unwrap_iter(self: SizedIter[L, n] @ owned) -> L:
        """Extracts the actual iterator."""

    @guppy.custom(NoopCompiler())
    def __iter__(self: SizedIter[L, n] @ owned) -> SizedIter[L, n]:  # type: ignore[type-arg]
        """Dummy implementation making sized iterators iterable themselves."""


@guppy.custom(checker=ResultChecker(), higher_order_value=False)
def result(tag, value):
    """Report a result with the given tag and value.

    This is the primary way to report results from the program back to the user.
    On Quantinuum systems a single shot execution will return a list of pairs of
    (tag, value).

    Args:
        tag: The tag of the result. Must be a string literal
        value: The value of the result. Currently supported value types are `int`,
        `nat`, `float`, and `bool`.
    """


@guppy.custom(checker=PanicChecker(), higher_order_value=False)
def panic(msg, *args):
    """Panic, throwing an error with the given message, and immediately exit the
    program, aborting any subsequent shots.

    Return type is arbitrary, as this function never returns.

    Args:
        msg: The message to display. Must be a string literal.
        args: Arbitrary extra inputs, will not affect the message. Only useful for
        consuming linear values.
    """


@guppy.custom(checker=ExitChecker(), higher_order_value=False)
def exit(msg: str, signal: int, *args):
    """Exit, reporting the given message and signal, and immediately exit the
    program. Subsequent shots may still run.

    Return type is arbitrary, as this function never returns.

    On Quantinuum systems only signals in the range 1<=signal<=1000 are supported.

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
    def __iter__(self: Range) -> Range:
        return self

    @guppy
    @no_type_check
    def __next__(self: Range) -> Option[tuple[int, Range]]:
        if self.next < self.stop:
            return some((self.next, Range(self.next + 1, self.stop)))
        return nothing()


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


@guppy.custom(checker=BarrierChecker(), higher_order_value=False)
def barrier(*args) -> None:
    """Barrier to guarantee that all operations before the barrier are completed before
    operations after the barrier are started."""


# Import `Option` since it's part of the default module. Has to be at the end of the
# file to avoid cyclic import.
#
# TODO: This is a temporary solution until https://github.com/CQCL/guppylang/issues/732
#  is properly addressed.
from guppylang.std.option import Option, nothing, some  # noqa: E402


# These should work equally well for signed integers if the need should arise
@guppy.hugr_op(
    external_op(
        "bytecast_int64_to_float64", args=[], ext=hugr.std.int.CONVERSIONS_EXTENSION
    )
)
def bytecast_nat_to_float(n: nat) -> float: ...


@guppy.hugr_op(
    external_op(
        "bytecast_float64_to_int64", args=[], ext=hugr.std.int.CONVERSIONS_EXTENSION
    )
)
def bytecast_float_to_nat(f: float) -> nat: ...
