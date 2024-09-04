from guppylang.decorator import guppy
from guppylang.prelude.builtins import nat, range
from guppylang.module import GuppyModule
from tests.util import compile_guppy

def test_range(validate, run_int_fn):
    module = GuppyModule("test_range")

    @guppy(module)
    def main() -> int:
        total = 0
        for x in range(5):
            total += x + 100 # Make the initial 0 obvious
        return total

    @guppy(module)
    def negative() -> int:
        total = 0
        for x in range(-3):
            total += 100 + x
        return total

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=510)
    run_int_fn(compiled, expected=0, fn_name="negative")
