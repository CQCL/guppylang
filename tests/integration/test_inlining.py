from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array


def test_inlining(validate, run_int_fn):
    module = GuppyModule("test")


    @guppy(module)
    def main() -> int:
        xs = array(1, 2, 4)
        ys = array(8, 16)
        i = xs[0]
        j = xs[1]
        k = ys[0]
        return i + j + k


    # print(module.compile_hugr().render_dot())

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=11)


