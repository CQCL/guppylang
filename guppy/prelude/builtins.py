"""Guppy module for builtin types and operations."""

# mypy: disable-error-code="empty-body, misc, override, no-untyped-def"

from guppy.custom import NoopCompiler, DefaultCallChecker
from guppy.decorator import guppy
from guppy.types import BoolType
from guppy.hugr import tys, ops
from guppy.module import GuppyModule
from guppy.prelude._internal import (
    logic_op,
    int_op,
    hugr_int_type,
    hugr_float_type,
    float_op,
    CoercingChecker,
    ReversingChecker,
    IntTruedivCompiler,
    FloatBoolCompiler,
    FloatDivmodCompiler,
    FloatFloordivCompiler,
    FloatModCompiler,
    DunderChecker,
    CallableChecker,
)


builtins = GuppyModule("builtins", import_builtins=False)


@guppy.extend_type(builtins, BoolType)
class Bool:
    @guppy.hugr_op(builtins, logic_op("And", [tys.BoundedNatArg(n=2)]))
    def __and__(self: bool, other: bool) -> bool:
        ...

    @guppy.custom(builtins, NoopCompiler())
    def __bool__(self: bool) -> bool:
        ...

    @guppy.hugr_op(builtins, int_op("ifrombool"))
    def __int__(self: bool) -> int:
        ...

    @guppy.hugr_op(builtins, logic_op("Or", [tys.BoundedNatArg(n=2)]))
    def __or__(self: bool, other: bool) -> bool:
        ...


@guppy.type(builtins, hugr_int_type, name="int")
class Int:
    @guppy.hugr_op(builtins, int_op("iabs"))  # TODO: Maybe wrong? (signed vs unsigned!)
    def __abs__(self: int) -> int:
        ...

    @guppy.hugr_op(builtins, int_op("iadd"))
    def __add__(self: int, other: int) -> int:
        ...

    @guppy.hugr_op(builtins, int_op("iand"))
    def __and__(self: int, other: int) -> int:
        ...

    @guppy.hugr_op(builtins, int_op("itobool"))
    def __bool__(self: int) -> bool:
        ...

    @guppy.custom(builtins, NoopCompiler())
    def __ceil__(self: int) -> int:
        ...

    @guppy.hugr_op(builtins, int_op("idivmod_s", num_params=2))
    def __divmod__(self: int, other: int) -> tuple[int, int]:
        ...

    @guppy.hugr_op(builtins, int_op("ieq"))
    def __eq__(self: int, other: int) -> bool:
        ...

    @guppy.hugr_op(builtins, int_op("convert_s", "arithmetic.conversions"))
    def __float__(self: int) -> float:
        ...

    @guppy.custom(builtins, NoopCompiler())
    def __floor__(self: int) -> int:
        ...

    @guppy.hugr_op(builtins, int_op("idiv_s", num_params=2))
    def __floordiv__(self: int, other: int) -> int:
        ...

    @guppy.hugr_op(builtins, int_op("ige_s"))
    def __ge__(self: int, other: int) -> bool:
        ...

    @guppy.hugr_op(builtins, int_op("igt_s"))
    def __gt__(self: int, other: int) -> bool:
        ...

    @guppy.custom(builtins, NoopCompiler())
    def __int__(self: int) -> int:
        ...

    @guppy.hugr_op(builtins, int_op("inot"))
    def __invert__(self: int) -> bool:
        ...

    @guppy.hugr_op(builtins, int_op("ile_s"))
    def __le__(self: int, other: int) -> bool:
        ...

    @guppy.hugr_op(builtins, int_op("ishl", num_params=2))  # TODO: RHS is unsigned
    def __lshift__(self: int, other: int) -> int:
        ...

    @guppy.hugr_op(builtins, int_op("ilt_s"))
    def __lt__(self: int, other: int) -> bool:
        ...

    @guppy.hugr_op(builtins, int_op("imod_s", num_params=2))
    def __mod__(self: int, other: int) -> int:
        ...

    @guppy.hugr_op(builtins, int_op("imul"))
    def __mul__(self: int, other: int) -> int:
        ...

    @guppy.hugr_op(builtins, int_op("ine"))
    def __ne__(self: int, other: int) -> bool:
        ...

    @guppy.hugr_op(builtins, int_op("ineg"))
    def __neg__(self: int) -> int:
        ...

    @guppy.hugr_op(builtins, int_op("ior"))
    def __or__(self: int, other: int) -> int:
        ...

    @guppy.custom(builtins, NoopCompiler())
    def __pos__(self: int) -> int:
        ...

    @guppy.hugr_op(builtins, ops.DummyOp(name="ipow"))  # TODO
    def __pow__(self: int, other: int) -> int:
        ...

    @guppy.hugr_op(builtins, int_op("iadd"), ReversingChecker(DefaultCallChecker()))
    def __radd__(self: int, other: int) -> int:
        ...

    @guppy.hugr_op(builtins, int_op("rand"), ReversingChecker(DefaultCallChecker()))
    def __rand__(self: int, other: int) -> int:
        ...

    @guppy.hugr_op(
        builtins,
        int_op("idivmod_s", num_params=2),
        ReversingChecker(DefaultCallChecker()),
    )
    def __rdivmod__(self: int, other: int) -> tuple[int, int]:
        ...

    @guppy.hugr_op(
        builtins, int_op("idiv_s", num_params=2), ReversingChecker(DefaultCallChecker())
    )
    def __rfloordiv__(self: int, other: int) -> int:
        ...

    @guppy.hugr_op(
        builtins, int_op("ishl", num_params=2), ReversingChecker(DefaultCallChecker())
    )  # TODO: RHS is unsigned
    def __rlshift__(self: int, other: int) -> int:
        ...

    @guppy.hugr_op(
        builtins, int_op("imod_s", num_params=2), ReversingChecker(DefaultCallChecker())
    )
    def __rmod__(self: int, other: int) -> int:
        ...

    @guppy.hugr_op(builtins, int_op("imul"), ReversingChecker(DefaultCallChecker()))
    def __rmul__(self: int, other: int) -> int:
        ...

    @guppy.hugr_op(builtins, int_op("ior"), ReversingChecker(DefaultCallChecker()))
    def __ror__(self: int, other: int) -> int:
        ...

    @guppy.custom(builtins, NoopCompiler())
    def __round__(self: int) -> int:
        ...

    @guppy.hugr_op(
        builtins, ops.DummyOp(name="ipow"), ReversingChecker(DefaultCallChecker())
    )  # TODO
    def __rpow__(self: int, other: int) -> int:
        ...

    @guppy.hugr_op(
        builtins, int_op("ishr", num_params=2), ReversingChecker(DefaultCallChecker())
    )  # TODO: RHS is unsigned
    def __rrshift__(self: int, other: int) -> int:
        ...

    @guppy.hugr_op(builtins, int_op("ishr", num_params=2))  # TODO: RHS is unsigned
    def __rshift__(self: int, other: int) -> int:
        ...

    @guppy.hugr_op(builtins, int_op("isub"), ReversingChecker(DefaultCallChecker()))
    def __rsub__(self: int, other: int) -> int:
        ...

    @guppy.custom(
        builtins, IntTruedivCompiler(), ReversingChecker(DefaultCallChecker())
    )
    def __rtruediv__(self: int, other: int) -> float:
        ...

    @guppy.hugr_op(builtins, int_op("ixor"), ReversingChecker(DefaultCallChecker()))
    def __rxor__(self: int, other: int) -> int:
        ...

    @guppy.hugr_op(builtins, int_op("isub"))
    def __sub__(self: int, other: int) -> int:
        ...

    @guppy.custom(builtins, IntTruedivCompiler())
    def __truediv__(self: int, other: int) -> float:
        ...

    @guppy.custom(builtins, NoopCompiler())
    def __trunc__(self: int) -> int:
        ...

    @guppy.hugr_op(builtins, int_op("ixor"))
    def __xor__(self: int, other: int) -> int:
        ...


@guppy.type(builtins, hugr_float_type, name="float")
class Float:
    @guppy.hugr_op(builtins, float_op("fabs"), CoercingChecker())
    def __abs__(self: float) -> float:
        ...

    @guppy.hugr_op(builtins, float_op("fadd"), CoercingChecker())
    def __add__(self: float, other: float) -> float:
        ...

    @guppy.custom(builtins, FloatBoolCompiler(), CoercingChecker())
    def __bool__(self: float) -> bool:
        ...

    @guppy.hugr_op(builtins, float_op("fceil"), CoercingChecker())
    def __ceil__(self: float) -> float:
        ...

    @guppy.custom(builtins, FloatDivmodCompiler(), CoercingChecker())
    def __divmod__(self: float, other: float) -> tuple[float, float]:
        ...

    @guppy.hugr_op(builtins, float_op("feq"), CoercingChecker())
    def __eq__(self: float, other: float) -> bool:
        ...

    @guppy.custom(builtins, NoopCompiler(), CoercingChecker())
    def __float__(self: float) -> float:
        ...

    @guppy.hugr_op(builtins, float_op("ffloor"), CoercingChecker())
    def __floor__(self: float) -> float:
        ...

    @guppy.custom(builtins, FloatFloordivCompiler(), CoercingChecker())
    def __floordiv__(self: float, other: float) -> float:
        ...

    @guppy.hugr_op(builtins, float_op("fge"), CoercingChecker())
    def __ge__(self: float, other: float) -> bool:
        ...

    @guppy.hugr_op(builtins, float_op("fgt"), CoercingChecker())
    def __gt__(self: float, other: float) -> bool:
        ...

    @guppy.hugr_op(
        builtins, float_op("trunc_s", "arithmetic.conversions"), CoercingChecker()
    )
    def __int__(self: float) -> int:
        ...

    @guppy.hugr_op(builtins, float_op("fle"), CoercingChecker())
    def __le__(self: float, other: float) -> bool:
        ...

    @guppy.hugr_op(builtins, float_op("flt"), CoercingChecker())
    def __lt__(self: float, other: float) -> bool:
        ...

    @guppy.custom(builtins, FloatModCompiler(), CoercingChecker())
    def __mod__(self: float, other: float) -> float:
        ...

    @guppy.hugr_op(builtins, float_op("fmul"), CoercingChecker())
    def __mul__(self: float, other: float) -> float:
        ...

    @guppy.hugr_op(builtins, float_op("fne"), CoercingChecker())
    def __ne__(self: float, other: float) -> bool:
        ...

    @guppy.hugr_op(builtins, float_op("fneg"), CoercingChecker())
    def __neg__(self: float, other: float) -> float:
        ...

    @guppy.custom(builtins, NoopCompiler(), CoercingChecker())
    def __pos__(self: float) -> float:
        ...

    @guppy.hugr_op(builtins, ops.DummyOp(name="fpow"))  # TODO
    def __pow__(self: float, other: float) -> float:
        ...

    @guppy.hugr_op(builtins, float_op("fadd"), ReversingChecker(CoercingChecker()))
    def __radd__(self: float, other: float) -> float:
        ...

    @guppy.custom(builtins, FloatDivmodCompiler(), ReversingChecker(CoercingChecker()))
    def __rdivmod__(self: float, other: float) -> tuple[float, float]:
        ...

    @guppy.custom(
        builtins, FloatFloordivCompiler(), ReversingChecker(CoercingChecker())
    )
    def __rfloordiv__(self: float, other: float) -> float:
        ...

    @guppy.custom(builtins, FloatModCompiler(), ReversingChecker(CoercingChecker()))
    def __rmod__(self: float, other: float) -> float:
        ...

    @guppy.hugr_op(builtins, float_op("fmul"), ReversingChecker(CoercingChecker()))
    def __rmul__(self: float, other: float) -> float:
        ...

    @guppy.hugr_op(builtins, ops.DummyOp(name="fround"))  # TODO
    def __round__(self: float) -> float:
        ...

    @guppy.hugr_op(
        builtins, ops.DummyOp(name="fpow"), ReversingChecker(DefaultCallChecker())
    )  # TODO
    def __rpow__(self: float, other: float) -> float:
        ...

    @guppy.hugr_op(builtins, float_op("fsub"), ReversingChecker(CoercingChecker()))
    def __rsub__(self: float, other: float) -> float:
        ...

    @guppy.hugr_op(builtins, float_op("fdiv"), ReversingChecker(CoercingChecker()))
    def __rtruediv__(self: float, other: float) -> float:
        ...

    @guppy.hugr_op(builtins, float_op("fsub"), CoercingChecker())
    def __sub__(self: float, other: float) -> float:
        ...

    @guppy.hugr_op(builtins, float_op("fdiv"), CoercingChecker())
    def __truediv__(self: float, other: float) -> float:
        ...

    @guppy.hugr_op(
        builtins, float_op("trunc_s", "arithmetic.conversions"), CoercingChecker()
    )
    def __trunc__(self: float) -> float:
        ...


@guppy.custom(builtins, checker=DunderChecker("__abs__"), higher_order_value=False)
def abs(x):
    ...


@guppy.custom(
    builtins, name="bool", checker=DunderChecker("__bool__"), higher_order_value=False
)
def _bool(x):
    ...


@guppy.custom(builtins, checker=CallableChecker(), higher_order_value=False)
def callable(x):
    ...


@guppy.custom(
    builtins, checker=DunderChecker("__divmod__", num_args=2), higher_order_value=False
)
def divmod(x, y):
    ...


@guppy.custom(
    builtins, name="float", checker=DunderChecker("__float__"), higher_order_value=False
)
def _float(x, y):
    ...


@guppy.custom(
    builtins, name="int", checker=DunderChecker("__int__"), higher_order_value=False
)
def _int(x):
    ...


@guppy.custom(
    builtins, checker=DunderChecker("__pow__", num_args=2), higher_order_value=False
)
def pow(x, y):
    ...


@guppy.custom(builtins, checker=DunderChecker("__round__"), higher_order_value=False)
def round(x):
    ...
