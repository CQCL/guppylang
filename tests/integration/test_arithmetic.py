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
