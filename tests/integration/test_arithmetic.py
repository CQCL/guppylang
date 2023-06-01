from guppy.compiler import guppy
from tests.integration.util import validate


def test_arith_basic(tmp_path):
    @guppy
    def add(x: int, y: int) -> int:
        return x + y

    validate(add, tmp_path)


def test_constant(tmp_path):
    @guppy
    def const() -> float:
        return 42.0

    validate(const, tmp_path)


def test_ann_assign(tmp_path):
    @guppy
    def add(x: int) -> int:
        x += 1
        return x

    validate(add, tmp_path)


def test_float_coercion(tmp_path):
    @guppy
    def coerce(x: int, y: float) -> float:
        return x * y

    validate(coerce, tmp_path)


def test_arith_big(tmp_path):
    @guppy
    def arith(x: int, y: float, z: int) -> bool:
        a = x ** y + 3 * z
        b = -8 >= a > 5 or (x * y == 0 and a % 3 < x)
        return b

    validate(arith, tmp_path)
