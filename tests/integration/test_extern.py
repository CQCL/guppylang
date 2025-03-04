import pytest

from hugr import ops, val

from guppylang.decorator import guppy
from guppylang.module import GuppyModule


def test_extern_float(validate):
    module = GuppyModule("module")

    guppy.extern("ext", ty="float", module=module)

    @guppy(module)
    def main() -> float:
        return ext + ext  # noqa: F821

    package = module.compile()
    validate(package)

    hg = package.module
    [c] = [data.op for n, data in hg.nodes() if isinstance(data.op, ops.Const)]
    assert isinstance(c.val, val.Extension)
    assert c.val.val["symbol"] == "ext"


def test_extern_alt_symbol(validate):
    module = GuppyModule("module")

    guppy.extern("ext", ty="int", symbol="foo", module=module)

    @guppy(module)
    def main() -> int:
        return ext  # noqa: F821

    package = module.compile()
    validate(package)

    hg = package.module
    [c] = [data.op for n, data in hg.nodes() if isinstance(data.op, ops.Const)]
    assert isinstance(c.val, val.Extension)
    assert c.val.val["symbol"] == "foo"


def test_extern_tuple(validate):
    module = GuppyModule("module")

    guppy.extern("ext", ty="tuple[int, float]", module=module)

    @guppy(module)
    def main() -> float:
        x, y = ext  # noqa: F821
        return x + y

    validate(module.compile())


@pytest.mark.skip("See https://github.com/CQCL/guppylang/issues/827")
def test_extern_conditional_assign(validate):
    module = GuppyModule("module")

    guppy.extern("x", ty="int", module=module)

    @guppy(module)
    def main(b: bool) -> int:
        if b:
            x = 4
        return x

    validate(module.compile())
