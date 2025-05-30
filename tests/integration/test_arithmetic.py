from guppylang.decorator import guppy
from guppylang.std.angles import angle, pi
from guppylang.std.builtins import nat
from tests.util import compile_guppy


def test_negative(validate, run_int_fn):
    @guppy
    def negative() -> int:
        return 2 - 42

    compiled = guppy.compile(negative)
    validate(compiled)
    run_int_fn(compiled, expected=-40, fn_name="negative")


def test_arith_basic(validate, run_int_fn):
    @guppy
    def add(x: int, y: int) -> int:
        return x + y

    @guppy
    def main() -> int:
        return add(40, 2)

    compiled = guppy.compile(main)
    validate(compiled)
    run_int_fn(compiled, 42)


def test_constant(validate):
    @compile_guppy
    def const() -> float:
        return 42.0

    validate(const)


def test_nat_literal(validate):
    @compile_guppy
    def const() -> nat:
        return 42

    validate(const)


def test_aug_assign(validate, run_int_fn):
    @guppy
    def add(x: int) -> int:
        x += 1
        return x

    @guppy
    def main() -> int:
        return add(5)

    compiled = guppy.compile(main)
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


def test_angle_arith(validate):
    @guppy
    def main(a1: angle, a2: angle) -> bool:
        a3 = -a1 + a2 * -3
        a3 -= a1
        a3 += 2 * a1
        return a3 / 3 == -a2

    validate(guppy.compile(main))


def test_angle_arith_float(validate):
    @guppy
    def main(a1: angle, a2: angle) -> bool:
        a3 = -a1 + a2 * -3.5
        a3 -= a1
        a3 += 2.2 * a1
        return a3 / 3.9 == -a2

    validate(guppy.compile(main))


def test_implicit_coercion(validate):
    @compile_guppy
    def coerce(x: nat) -> float:
        y: int = x
        z: float = y
        a: float = 1
        return z + a

    validate(coerce)


def test_angle_float_coercion(validate):
    @guppy
    def main(f: float) -> tuple[angle, float]:
        a = angle(f)
        return a, float(a)

    validate(guppy.compile(main))


def test_angle_pi(validate):
    @guppy
    def main() -> angle:
        a = 2 * pi
        a += -pi / 3
        a += 3 * pi / 2
        return a

    validate(guppy.compile(main))


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
    @guppy
    def double_add(x: int) -> int:
        return x + x

    @guppy
    def double_mul(x: int) -> int:
        return x * 2

    @guppy
    def quad(x: int) -> int:
        y = double_add(x)
        z = double_mul(x)
        return y + z

    @guppy
    def run_quad() -> int:
        return quad(42)

    @guppy
    def neg(x: int) -> int:
        return -x

    @guppy
    def run_neg() -> int:
        return neg(42)

    @guppy
    def div(x: int, y: int) -> int:
        return x // y

    @guppy
    def run_div() -> int:
        return div(-42, 21)

    @guppy
    def run_rem() -> int:
        return 11 % 3

    @guppy
    def main() -> None:
        run_quad()
        run_neg()
        run_div()
        run_rem()

    hugr = guppy.compile(main)
    validate(hugr)
    run_int_fn(hugr, expected=168, fn_name="run_quad")
    run_int_fn(hugr, expected=-42, fn_name="run_neg")
    run_int_fn(hugr, expected=-2, fn_name="run_div")
    run_int_fn(hugr, expected=2, fn_name="run_rem")


def test_angle_exec(validate, run_float_fn_approx):
    @guppy
    def main() -> float:
        a1 = pi
        a2 = pi * 2
        a3 = -a1 + a2 * -3
        a3 -= a1
        a3 += 2 * a1
        return float(a3)

    hugr = guppy.compile(main)
    validate(hugr)
    import math

    run_float_fn_approx(hugr, expected=-6 * math.pi)


def test_xor(validate, run_int_fn):
    @guppy
    def main() -> int:
        return int(True ^ False ^ False)

    compiled = guppy.compile(main)
    validate(compiled)
    run_int_fn(compiled, 1)

    @guppy
    def main() -> int:
        return int(True ^ False ^ False ^ True)

    compiled = main.compile()
    run_int_fn(compiled, 0)


def test_pow(validate, run_int_fn) -> None:
    @guppy
    def main() -> int:
        return -(3**3) + 4**2

    compiled = guppy.compile(main)
    validate(compiled)
    run_int_fn(compiled, -11)


def test_float_to_int(validate, run_int_fn) -> None:
    @guppy
    def main() -> int:
        return int(-2.75)

    compiled = guppy.compile(main)
    validate(compiled)
    run_int_fn(compiled, -2)


def test_float_to_nat(validate, run_int_fn) -> None:
    @guppy
    def main() -> nat:
        return nat(2.75)

    compiled = guppy.compile(main)
    validate(compiled)
    run_int_fn(compiled, 2)


def test_shift(validate, run_int_fn) -> None:
    @guppy
    def main() -> int:
        nats = (nat(7) << nat(2)) - (nat(1) << nat(3))
        return int(nats) + (2 << 3) + (53 >> 3)

    compiled = guppy.compile(main)
    validate(compiled)
    run_int_fn(compiled, 42)

def test_divmod(validate, run_int_fn) -> None:
    @guppy
    def quot() -> int:
        return -1 // 4

    @guppy
    def rem() -> int:
        return -1 % 4

    @guppy
    def main() -> None:
        quot()
        rem()

    compiled = guppy.compile(main)
    validate(compiled)
    run_int_fn(compiled, -1, "quot")
    run_int_fn(compiled, 3, "rem")
