from guppylang.prelude.builtins import result, nat, array
from tests.util import compile_guppy


def test_basic(validate):
    @compile_guppy
    def main(x: int) -> None:
        result("foo", x)

    validate(main)


def test_multi(validate):
    @compile_guppy
    def main(w: nat, x: int, y: float, z: bool) -> None:
        result("a", w)
        result("b", x)
        result("c", y)
        result("d", z)

    validate(main)


def test_array(validate):
    @compile_guppy
    def main(
        w: array[nat, 42], x: array[int, 5], y: array[float, 1], z: array[bool, 0]
    ) -> None:
        result("a", w)
        result("b", x)
        result("c", y)
        result("d", z)

    validate(main)


def test_same_tag(validate):
    @compile_guppy
    def main(x: int, y: float, z: bool) -> None:
        result("foo", x)
        result("foo", y)
        result("foo", z)

    validate(main)
