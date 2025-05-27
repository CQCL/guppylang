import pytest

from hugr import ops, val

from guppylang.decorator import guppy


def test_extern_float(validate):
    ext = guppy.extern("ext", ty="float")

    @guppy
    def main() -> float:
        return ext + ext  # noqa: F821

    package = guppy.compile(main)
    validate(package)

    hg = package.module
    [c] = [data.op for n, data in hg.nodes() if isinstance(data.op, ops.Const)]
    assert isinstance(c.val, val.Extension)
    assert c.val.val["symbol"] == "ext"


def test_extern_alt_symbol(validate):
    ext = guppy.extern("ext", ty="int", symbol="foo")

    @guppy
    def main() -> int:
        return ext  # noqa: F821

    package = guppy.compile(main)
    validate(package)

    hg = package.module
    [c] = [data.op for n, data in hg.nodes() if isinstance(data.op, ops.Const)]
    assert isinstance(c.val, val.Extension)
    assert c.val.val["symbol"] == "foo"


def test_extern_tuple(validate):
    ext = guppy.extern("ext", ty="tuple[int, float]")

    @guppy
    def main() -> float:
        x, y = ext  # noqa: F821
        return x + y

    validate(guppy.compile(main))


@pytest.mark.skip("See https://github.com/CQCL/guppylang/issues/827")
def test_extern_conditional_assign(validate):
    x = guppy.extern("x", ty="int")

    @guppy
    def main(b: bool) -> int:
        if b:
            x = 4
        return x

    validate(guppy.compile(main))
