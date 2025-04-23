from guppylang.decorator import guppy
from guppylang.std.builtins import nat
from guppylang.module import GuppyModule

def test_roundtrip(validate, run_int_fn):
    module = GuppyModule("bytecast_roundtrip")

    @guppy(module)
    def roundtrip(n: nat) -> nat:
        f = bytecast_nat_to_float(n)
        return bytecast_float_to_nat(f)

    @guppy(module)
    def main() -> nat:
        x = roundtrip(42)
        return x

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=42)

def test_roundtrip2(validate, run_float_fn_approx):
    module = GuppyModule("bytecast_roundtrip")

    @guppy(module)
    def roundtrip(f: float) -> float:
        n = bytecast_float_to_nat(f)
        f2 =  bytecast_nat_to_float(n)
        n2 = bytecast_float_to_nat(f2)
        return bytecast_nat_to_float(n2)

    @guppy(module)
    def main() -> float:
        x = roundtrip(42.0)
        return x

    compiled = module.compile()
    validate(compiled)
    run_float_fn_approx(compiled, expected=42.0)
