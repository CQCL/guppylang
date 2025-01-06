import pytest

from guppylang import GuppyModule, guppy


@pytest.mark.xfail
def test_hand(validate):
    """Regression test ensuring that pytest terminates, even if the Guppy compiler
    throws an error.

    See https://github.com/CQCL/guppylang/issues/569
    """
    module = GuppyModule("test")

    @guppy(module)
    def test() -> int:
        return a  # Intentional use of an undefined variable

    validate(module.compile())
