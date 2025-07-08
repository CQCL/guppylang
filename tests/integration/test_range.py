from guppylang.decorator import guppy
from guppylang.std.builtins import range, SizedIter, Range, py


def test_range(validate, run_int_fn):
    @guppy
    def main() -> int:
        total = 0
        for x in range(5):
            total += x + 100  # Make the initial 0 obvious
        return total

    @guppy
    def negative() -> int:
        total = 0
        for x in range(-3):
            total += 100 + x
        return total

    @guppy
    def non_static() -> int:
        total = 0
        n = 4
        for x in range(n + 1):
            total += x + 100  # Make the initial 0 obvious
        return total

    compiled = guppy.compile(main)
    validate(compiled)
    run_int_fn(compiled, expected=510)

    compiled = guppy.compile(negative)
    validate(compiled)
    run_int_fn(compiled, expected=0, fn_name="negative")

    compiled = guppy.compile(non_static)
    validate(compiled)
    run_int_fn(compiled, expected=510, fn_name="non_static")


def test_static_size(validate):
    @guppy
    def negative() -> SizedIter[Range, 10]:
        return range(10)

    validate(guppy.compile(negative))


def test_py_size(validate):
    n = 10

    @guppy
    def negative() -> SizedIter[Range, 10]:
        return range(py(n))

    validate(guppy.compile(negative))


def test_static_generic_size(validate):
    n = guppy.nat_var("n")

    @guppy
    def negative() -> SizedIter[Range, n]:
        return range(n)

    validate(guppy.compile(negative))
