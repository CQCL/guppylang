from guppylang.prelude.builtins import result
from tests.util import compile_guppy


def test_single(validate):
    @compile_guppy
    def main(x: int) -> None:
        result(0, x)

    validate(main)


def test_value(validate):
    @compile_guppy
    def main(x: int) -> None:
        return result(0, x)

    validate(main)


def test_nested(validate):
    @compile_guppy
    def main(x: int, y: float, z: bool) -> None:
        result(42, (x, (y, z)))

    validate(main)


def test_multi(validate):
    @compile_guppy
    def main(x: int, y: float, z: bool) -> None:
        result(0, x)
        result(1, y)
        result(2, z)

    validate(main)


def test_same_tag(validate):
    @compile_guppy
    def main(x: int, y: float, z: bool) -> None:
        result(0, x)
        result(0, y)
        result(0, z)

    validate(main)
