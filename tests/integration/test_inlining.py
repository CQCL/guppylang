from hugr import ops
from hugr.std.int import IntVal

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array, owned, mem_swap
from tests.util import compile_guppy

from guppylang.std.quantum import qubit, discard
import guppylang.std.quantum as quantum

def test_inlining1(validate):
    module = GuppyModule("test")


    @guppy(module)
    def main(xs: array[int, 42], ys: array[int, 22]) -> None:
        i = xs[0]
        j = ys[1]

    print(module.compile_hugr().render_dot())
    assert False
    validate(module.compile())