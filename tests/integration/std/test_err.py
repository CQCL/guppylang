from guppylang.decorator import guppy
from guppylang.std.err import Result, ok, err
from guppylang.std.quantum import qubit  # noqa: TCH001


def test_ok(run_int_fn):
    @guppy
    def main() -> int:
        x: Result[int, qubit] = ok(100)
        is_ok = 1 if x.is_ok() else 0
        is_err = 10 if x.is_err() else 0
        return is_ok + is_err + x.unwrap()

    run_int_fn(main, expected=101)


def test_err(run_int_fn):
    @guppy
    def main() -> int:
        x: Result[qubit, int] = err(100)
        is_ok = 1 if x.is_ok() else 0
        is_err = 10 if x.is_err() else 0
        return is_ok + is_err + x.unwrap_err()

    run_int_fn(main, expected=110)
