from guppylang.decorator import guppy
from guppylang.std.builtins import nat
from guppylang.module import GuppyModule


def test_roundtrip(validate, run_int_fn):
    module = GuppyModule("bytecast_roundtrip")

    @guppy(module)
    def roundtrip(n: nat) -> nat:
        f: float = bytecast(n)
        return bytecast(f)

    @guppy(module)
    def main() -> nat:
        x: nat = roundtrip(42)
        return x

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=42)


def test_roundtrip2(validate, run_float_fn_approx):
    module = GuppyModule("bytecast_roundtrip")

    @guppy(module)
    def roundtrip(f: float) -> float:
        n: nat = bytecast(f)
        f2: float = bytecast(n)
        n2: nat = bytecast(f2)
        return bytecast(n2)

    @guppy(module)
    def main() -> float:
        x = roundtrip(42.0)
        return x

    compiled = module.compile()
    validate(compiled)
    run_float_fn_approx(compiled, expected=42.0)
