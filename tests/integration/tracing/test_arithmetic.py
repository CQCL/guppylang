from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import nat


def test_int(validate, run_int_fn):
    module = GuppyModule("module")

    @guppy.comptime(module)
    def pos(x: int) -> int:
        return +x

    @guppy.comptime(module)
    def neg(x: int) -> int:
        return -x

    @guppy.comptime(module)
    def add(x: int, y: int) -> int:
        return 1 + (x + (y + 2))

    @guppy.comptime(module)
    def sub(x: int, y: int) -> int:
        return 1 - (x - (y - 2))

    @guppy.comptime(module)
    def mul(x: int, y: int) -> int:
        return 1 * (x * (y * 2))

    @guppy.comptime(module)
    def div(x: int, y: int) -> int:
        return 100 // (x // (y // 2))

    @guppy.comptime(module)
    def mod(x: int, y: int) -> int:
        return 15 % (x % (y % 10))

    @guppy.comptime(module)
    def pow(x: int, y: int) -> int:
        return 4 ** (x ** (y ** 0))

    @guppy(module)
    def main() -> None:
        """Dummy main function"""

    compiled = module.compile()
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
    module = GuppyModule("module")

    @guppy.comptime(module)
    def pos(x: float) -> float:
        return +x

    @guppy.comptime(module)
    def neg(x: float) -> float:
        return -x

    @guppy.comptime(module)
    def add(x: float, y: float) -> float:
        return 1 + (x + (y + 2))

    @guppy.comptime(module)
    def sub(x: float, y: float) -> float:
        return 1 - (x - (y - 2))

    @guppy.comptime(module)
    def mul(x: float, y: float) -> float:
        return 1 * (x * (y * 2))

    @guppy.comptime(module)
    def div(x: float, y: float) -> float:
        return 100 / (x / (y / 2))

    # TODO: Requires lowering of `ffloor` op: https://github.com/CQCL/hugr/issues/1905
    # @guppy.comptime(module)
    # def floordiv(x: float, y: float) -> float:
    #     return 100 // (x // (y // 2))

    # TODO: Requires lowering of `fpow` op: https://github.com/CQCL/hugr/issues/1905
    # @guppy.comptime(module)
    # def pow(x: float, y: float) -> float:
    #     return 4 ** (x ** (y ** 0.5))

    @guppy(module)
    def main() -> None:
        """Dummy main function"""

    compiled = module.compile()
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


def test_dunder_coercions(validate):
    module = GuppyModule("module")

    @guppy.comptime(module)
    def test1(x: int) -> float:
        return 1.0 + x

    @guppy.comptime(module)
    def test2(x: int) -> float:
        return x + 1.0

    @guppy.comptime(module)
    def test3(x: float) -> float:
        return 1 + x

    @guppy.comptime(module)
    def test4(x: float) -> float:
        return x + 1

    @guppy.comptime(module)
    def test4(x: int, y: float) -> float:
        return x + y

    @guppy.comptime(module)
    def test5(x: float, y: int) -> float:
        return x + y

    validate(module.compile())
