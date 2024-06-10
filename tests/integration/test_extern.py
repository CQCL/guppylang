from hugr.serialization import ops

from guppylang.decorator import guppy
from guppylang.module import GuppyModule


def test_extern_float(validate):
    module = GuppyModule("module")

    guppy.extern(module, "ext", ty="float")

    @guppy(module)
    def main() -> float:
        return ext + ext  # noqa: F821

    hg = module.compile()
    validate(hg)

    [c] = [n.op.root for n in hg.nodes() if isinstance(n.op.root, ops.Const)]
    assert isinstance(c.v.root, ops.ExtensionValue)
    assert c.v.root.value.v["symbol"] == "ext"


def test_extern_alt_symbol(validate):
    module = GuppyModule("module")

    guppy.extern(module, "ext", ty="int", symbol="foo")

    @guppy(module)
    def main() -> int:
        return ext  # noqa: F821

    hg = module.compile()
    validate(hg)

    [c] = [n.op.root for n in hg.nodes() if isinstance(n.op.root, ops.Const)]
    assert isinstance(c.v.root, ops.ExtensionValue)
    assert c.v.root.value.v["symbol"] == "foo"

def test_extern_tuple(validate):
    module = GuppyModule("module")

    guppy.extern(module, "ext", ty="tuple[int, float]")

    @guppy(module)
    def main() -> float:
        x, y = ext  # noqa: F821
        return x + y

    validate(module.compile())
