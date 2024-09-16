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

    hg = package.modules[0]
    consts = [data.op for n, data in hg.nodes() if isinstance(data.op, ops.Const)]
    if len(consts) > 1:
        pytest.xfail(reason="hugr-includes-whole-stdlib")
    [c] = consts
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

    hg = package.modules[0]
    consts = [data.op for n, data in hg.nodes() if isinstance(data.op, ops.Const)]
    if len(consts) > 1:
        pytest.xfail(reason="hugr-includes-whole-stdlib")
    [c] = consts
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
