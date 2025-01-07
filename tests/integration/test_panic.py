from typing import no_type_check

from guppylang.std.builtins import panic
from tests.util import compile_guppy


def test_basic(validate):
    @compile_guppy
    @no_type_check
    def main() -> None:
        panic("I panicked!")

    validate(main)


def test_discard(validate):
    @compile_guppy
    @no_type_check
    def main() -> None:
        a = 1 + 2
        panic("I panicked!", False, a)

    validate(main)
