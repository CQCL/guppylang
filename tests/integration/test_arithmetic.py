import pytest
from guppylang.decorator import guppy
from guppylang.prelude.builtins import nat
from guppylang.module import GuppyModule
from tests.util import compile_guppy


def test_negative(validate, run_int_fn):
    module = GuppyModule("test_negative")

    @guppy(module)
    def negative() -> int:
        return 2 - 42

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=-40, fn_name="negative")


def test_arith_basic(validate, run_int_fn):
    module = GuppyModule("test_arith")

    @guppy(module)
    def add(x: int, y: int) -> int:
        return x + y

    @guppy(module)
    def main() -> int:
        return add(40, 2)

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, 42)


def test_constant(validate):
    @compile_guppy
    def const() -> float:
        return 42.0

    validate(const)


def test_aug_assign(validate, run_int_fn):
    module = GuppyModule("test_aug_assign")

    @guppy(module)
    def add(x: int) -> int:
        x += 1
        return x

    @guppy(module)
    def main() -> int:
        return add(5)

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, 6)


@pytest.mark.skip(reason="trunc_u has an invalid signature")
def test_nat(validate):
    @compile_guppy
    def foo(
        a: nat, b: nat, c: bool, d: int, e: float
    ) -> tuple[nat, bool, int, float, float]:
        b, c, d, e = nat(b), nat(c), nat(d), nat(e)
        x = a + b * c // d - e
        y = e / b
        return x, bool(x), int(x), float(x), y

    validate(foo)


@pytest.mark.skip(reason="trunc_u has an invalid signature")
def test_nat2(validate):
    @compile_guppy
    def foo(
        a: nat, b: nat, c: bool, d: int, e: float
    ) -> tuple[nat, bool, int, float, float]:
        b, c, d, e = nat(b), nat(c), nat(d), nat(e)
        x = a + b * c // d - e
        y = e / b
        return x, bool(x), int(x), float(x), y

    validate(foo)


def test_float_coercion(validate):
    @compile_guppy
    def coerce(x: int, y: float) -> float:
        return x * y

    validate(coerce)


def test_arith_big(validate):
    @compile_guppy
    def arith(x: int, y: float, z: int) -> bool:
        a = x // y + 3 * z
        b = -8 >= a > 5 or (x * y == 0 and a % 3 < x)
        return b

    validate(arith)


def test_shortcircuit_assign1(validate):
    @compile_guppy
    def foo(x: bool, y: int) -> bool:
        if (z := x) and y > 0:
            return z
        return not z

    validate(foo)


def test_shortcircuit_assign2(validate):
    @compile_guppy
    def foo(x: bool, y: int) -> bool:
        if y > 0 and (z := x):
            return z
        return False

    validate(foo)


def test_shortcircuit_assign3(validate):
    @compile_guppy
    def foo(x: bool, y: int) -> bool:
        if (z := x) or y > 0:
            return z
        return z

    validate(foo)


def test_shortcircuit_assign4(validate):
    @compile_guppy
    def foo(x: bool, y: int) -> bool:
        if y > 0 or (z := x):
            return False
        return z

    validate(foo)


def test_supported_ops(validate, run_int_fn):
    module = GuppyModule("supported_ops")

    @guppy(module)
    def double_add(x: int) -> int:
        return x + x

    @guppy(module)
    def double_mul(x: int) -> int:
        return x * 2

    @guppy(module)
    def quad(x: int) -> int:
        y = double_add(x)
        z = double_mul(x)
        return y + z

    @guppy(module)
    def run_quad() -> int:
        return quad(42)

    @guppy(module)
    def neg(x: int) -> int:
        return -x

    @guppy(module)
    def run_neg() -> int:
        return neg(42)

    @guppy(module)
    def div(x: int, y: int) -> int:
        return x // y

    @guppy(module)
    def run_div() -> int:
        return div(-42, 21)

    @guppy(module)
    def run_rem() -> int:
        return 11 % 3

    hugr = module.compile()
    validate(hugr)
    run_int_fn(hugr, expected=168, fn_name="run_quad")
    run_int_fn(hugr, expected=-42, fn_name="run_neg")
    run_int_fn(hugr, expected=-2, fn_name="run_div")
    run_int_fn(hugr, expected=2, fn_name="run_rem")
