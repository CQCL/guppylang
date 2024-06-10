from guppylang.decorator import guppy
from guppylang.module import GuppyModule


def test_extern_float(validate):
    module = GuppyModule("module")

    guppy.extern(module, "ext", ty="float")

    @guppy(module)
    def main() -> float:
        return ext + ext  # noqa: F821

    validate(module.compile())


def test_extern_tuple(validate):
    module = GuppyModule("module")

    guppy.extern(module, "ext", ty="tuple[int, float]")

    @guppy(module)
    def main() -> float:
        x, y = ext  # noqa: F821
        return x + y

    validate(module.compile())
