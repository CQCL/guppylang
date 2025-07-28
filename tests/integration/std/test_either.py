from guppylang.decorator import guppy
from guppylang.std.either import Either, left, right
from guppylang.std.quantum import qubit  # noqa: TCH001


def test_left(run_int_fn):
    @guppy
    def main() -> int:
        x: Either[int, qubit] = left(100)
        is_left = 1 if x.is_left() else 0
        is_right = 10 if x.is_right() else 0
        return is_left + is_right + x.unwrap_left()

    run_int_fn(main, expected=101)


def test_right(run_int_fn):
    @guppy
    def main() -> int:
        x: Either[qubit, int] = right(100)
        is_left = 1 if x.is_left() else 0
        is_right = 10 if x.is_right() else 0
        return is_left + is_right + x.unwrap_right()

    run_int_fn(main, expected=110)


def test_to_option(run_int_fn):
    @guppy
    def main() -> int:
        l: Either[int, float] = left(1)
        r: Either[float, int] = right(10)
        l.try_into_right().unwrap_nothing()
        r.try_into_left().unwrap_nothing()
        return l.try_into_left().unwrap() + r.try_into_right().unwrap()

    run_int_fn(main, expected=11)
