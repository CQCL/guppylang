from guppylang.decorator import guppy
from guppylang.std.builtins import range, SizedIter, Range, py


def test_range(run_int_fn):
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

    run_int_fn(main, expected=510)

    run_int_fn(negative, expected=0)

    run_int_fn(non_static, expected=510)


def test_static_size(validate):
    @guppy
    def negative() -> SizedIter[Range, 10]:
        return range(10)

    validate(negative.compile())


def test_py_size(validate):
    n = 10

    @guppy
    def negative() -> SizedIter[Range, 10]:
        return range(py(n))

    validate(negative.compile())


def test_static_generic_size(validate):
    n = guppy.nat_var("n")

    @guppy
    def negative() -> SizedIter[Range, n]:
        return range(n)

    validate(negative.compile())
