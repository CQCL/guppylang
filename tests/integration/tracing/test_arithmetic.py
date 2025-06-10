from guppylang.decorator import guppy
from guppylang.std.angles import angle, pi
from guppylang.std.builtins import nat

from hugr.std.int import IntVal


def test_int(validate, run_int_fn):
    @guppy.comptime
    def pos(x: int) -> int:
        return +x

    @guppy.comptime
    def neg(x: int) -> int:
        return -x

    @guppy.comptime
    def add(x: int, y: int) -> int:
        return 1 + (x + (y + 2))

    @guppy.comptime
    def sub(x: int, y: int) -> int:
        return 1 - (x - (y - 2))

    @guppy.comptime
    def mul(x: int, y: int) -> int:
        return 1 * (x * (y * 2))

    @guppy.comptime
    def div(x: int, y: int) -> int:
        return 100 // (x // (y // 2))

    @guppy.comptime
    def mod(x: int, y: int) -> int:
        return 15 % (x % (y % 10))

    @guppy.comptime
    def pow(x: int, y: int) -> int:
        return 4 ** (x ** (y ** 0))

    @guppy
    def main() -> None:
        """Dummy main function"""
        pos, neg, add, sub, mul, div, mod, pow

    compiled = guppy.compile(main)
    validate(compiled)

    run_int_fn(compiled, 10, "pos", [10])
    run_int_fn(compiled, -10, "neg", [10])
    run_int_fn(compiled, 2, "add", [3, -4])
    run_int_fn(compiled, -8, "sub", [3, -4])
    run_int_fn(compiled, -24, "mul", [3, -4])
    run_int_fn(compiled, 20, "div", [25, 10])
    run_int_fn(compiled, 7, "mod", [8, 9])
    run_int_fn(compiled, 16, "pow", [2, 100])


def test_float(validate, run_float_fn_approx):
    @guppy.comptime
    def pos(x: float) -> float:
        return +x

    @guppy.comptime
    def neg(x: float) -> float:
        return -x

    @guppy.comptime
    def add(x: float, y: float) -> float:
        return 1 + (x + (y + 2))

    @guppy.comptime
    def sub(x: float, y: float) -> float:
        return 1 - (x - (y - 2))

    @guppy.comptime
    def mul(x: float, y: float) -> float:
        return 1 * (x * (y * 2))

    @guppy.comptime
    def div(x: float, y: float) -> float:
        return 100 / (x / (y / 2))

    # TODO: Requires lowering of `ffloor` op: https://github.com/CQCL/hugr/issues/1905
    # @guppy.comptime
    # def floordiv(x: float, y: float) -> float:
    #     return 100 // (x // (y // 2))

    # TODO: Requires lowering of `fpow` op: https://github.com/CQCL/hugr/issues/1905
    # @guppy.comptime
    # def pow(x: float, y: float) -> float:
    #     return 4 ** (x ** (y ** 0.5))

    @guppy
    def main() -> None:
        """Dummy main function"""
        pos, neg, add, sub, mul, div

    compiled = guppy.compile(main)
    validate(compiled)

    run_float_fn_approx(compiled, 10.5, "pos", [10.5])
    run_float_fn_approx(compiled, -10.5, "neg", [10.5])
    run_float_fn_approx(compiled, 1.5, "add", [3, -4.5])
    run_float_fn_approx(compiled, -8.5, "sub", [3, -4.5])
    run_float_fn_approx(compiled, -27.0, "mul", [3, -4.5])
    run_float_fn_approx(compiled, 400.0, "div", [0.5, 4])

    # TODO: Requires lowering of `ffloor` op: https://github.com/CQCL/hugr/issues/1905
    # run_float_fn_approx(compiled, ... "div", [...])

    # TODO: Requires lowering of `fpow` op: https://github.com/CQCL/hugr/issues/1905
    # run_float_fn_approx(compiled, ..., "pow", [...])


def test_angle(validate):
    @guppy.comptime
    def neg(x: angle) -> angle:
        return -x

    @guppy.comptime
    def neg_pi() -> angle:
        return -pi

    @guppy.comptime
    def add(x: angle, y: float) -> angle:
        return pi + (x + angle(y) + pi)

    @guppy.comptime
    def sub(x: float, y: angle) -> angle:
        return pi - (angle(x) - (y - pi))

    @guppy.comptime
    def mul(x: float, y: angle) -> angle:
        return 1.5 * (x * (y * 2))

    @guppy.comptime
    def div(x: angle, y: float) -> angle:
        return x / y

    @guppy
    def main() -> None:
        """Dummy main function"""
        add, sub, mul, div

    validate(guppy.compile(main))


def test_dunder_coercions(validate):
    @guppy.comptime
    def test1(x: int) -> float:
        return 1.0 + x

    @guppy.comptime
    def test2(x: int) -> float:
        return x + 1.0

    @guppy.comptime
    def test3(x: float) -> float:
        return 1 + x

    @guppy.comptime
    def test4(x: float) -> float:
        return x + 1

    @guppy.comptime
    def test5(x: int, y: float) -> float:
        return x + y

    @guppy.comptime
    def test6(x: float, y: int) -> float:
        return x + y

    validate(guppy.compile(test1))
    validate(guppy.compile(test2))
    validate(guppy.compile(test3))
    validate(guppy.compile(test4))
    validate(guppy.compile(test5))
    validate(guppy.compile(test6))



def test_const(validate):
    x = guppy.constant("x", "int", IntVal(10, 6))

    @guppy.comptime
    def test1() -> int:
        return -x

    @guppy.comptime
    def test2() -> int:
        return 1 + x

    @guppy.comptime
    def test2() -> int:
        return x * 2

    @guppy.comptime
    def test3() -> float:
        return 1.5 - x

    @guppy.comptime
    def test4() -> float:
        return x / 0.5

    validate(guppy.compile(test1))
    validate(guppy.compile(test2))
    validate(guppy.compile(test3))
    validate(guppy.compile(test4))
