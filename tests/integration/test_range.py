from guppylang.decorator import guppy
from guppylang.prelude.builtins import nat, range
from guppylang.module import GuppyModule
from tests.util import compile_guppy

def test_range(validate, run_int_fn):
    module = GuppyModule("test_aug_assign_loop")

    @guppy(module)
    def main() -> int:
        total = 0
        xs = range(5)
        for x in xs:
            total += 100 + x
        return total

    @guppy(module)
    def negative() -> int:
        total = 0
        xs = range(-3)
        for x in xs:
            total += 100 + x
        return total

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=510)
    run_int_fn(compiled, expected=0, fn_name="negative")