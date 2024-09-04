import pytest
from hugr import ops
from hugr.std.int import IntVal

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import array
from tests.util import compile_guppy


@pytest.mark.xfail(reason="hugr-includes-whole-stdlib")
def test_len(validate):
    module = GuppyModule("test")

    @guppy(module)
    def main(xs: array[float, 42]) -> int:
        return len(xs)

    hg = module.compile()
    validate(hg)

    [val] = [data.op for node, data in hg.nodes() if isinstance(data.op, ops.Const)]
    assert isinstance(val, ops.Const)
    assert isinstance(val.val, IntVal)
    assert val.val.v == 42


def test_index(validate):
    @compile_guppy
    def main(xs: array[int, 5], i: int) -> int:
        return xs[0] + xs[i] + xs[xs[2 * i]]

    validate(main)
