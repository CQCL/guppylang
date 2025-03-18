from guppylang import GuppyModule, guppy, quantum, qubit
from guppylang.std.qsystem.random import RNG
from guppylang.std.qsystem import random

def test_nat(validate, run_int_fn):
    module = GuppyModule("test_nat")
    module.load_all(random)

    @guppy(module)
    def main() -> 'nat':
        return nat(42)

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=42)


def test_ctx_lifecycle(validate, run_int_fn):
    module = GuppyModule("test_lifecycle")
    module.load_all(random)

    @guppy(module)
    def main() -> int:
        rng = RNG(0)
        rng.discard()
        return 0

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=0)

def test_rng_nat(validate, run_int_fn):
    module = GuppyModule("test_rng_nat")
    module.load_all(random)

    @guppy(module)
    def main() -> int:
        rng = RNG(0)
        x = rng.random_int()
        rng.discard()
        return x

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=0)
