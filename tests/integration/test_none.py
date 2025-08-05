import pytest

from guppylang.decorator import guppy


@pytest.mark.skip(reason="TODO: Testing release-checks. Unskip this")
def test_none(validate, run_int_fn):
    @guppy
    def foo() -> None:
        return None

    @guppy
    def bar(x: None, y: int) -> int:
        return y

    @guppy
    def main() -> int:
        return bar(foo(), 42)

    validate(main.compile())
    run_int_fn(main, expected=42)
