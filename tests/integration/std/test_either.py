from guppylang.decorator import guppy
from guppylang.std.either import Either, left, right
from guppylang.std.quantum import qubit


def test_left(validate, run_int_fn):
    @guppy
    def main() -> int:
        x: Either[int, qubit] = left(100)
        is_left = 1 if x.is_left() else 0
        is_right = 10 if x.is_right() else 0
        return is_left + is_right + x.unwrap_left()

    compiled = guppy.compile(main)
    validate(compiled)
    run_int_fn(compiled, expected=101)


def test_right(validate, run_int_fn):
    @guppy
    def main() -> int:
        x: Either[qubit, int] = right(100)
        is_left = 1 if x.is_left() else 0
        is_right = 10 if x.is_right() else 0
        return is_left + is_right + x.unwrap_right()

    compiled = guppy.compile(main)
    validate(compiled)
    run_int_fn(compiled, expected=110)


def test_to_option(validate, run_int_fn):
    @guppy
    def main() -> int:
        l: Either[int, float] = left(1)
        r: Either[float, int] = right(10)
        l.try_into_right().unwrap_nothing()
        r.try_into_left().unwrap_nothing()
        return l.try_into_left().unwrap() + r.try_into_right().unwrap()

    compiled = guppy.compile(main)
    validate(compiled)
    run_int_fn(compiled, expected=11)

