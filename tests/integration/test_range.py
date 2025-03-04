from guppylang.decorator import guppy
from guppylang.std.builtins import range, SizedIter, Range, py
from guppylang.module import GuppyModule

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

    @guppy(module)
    def non_static() -> int:
        total = 0
        n = 4
        for x in range(n + 1):
            total += x + 100  # Make the initial 0 obvious
        return total

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=510)
    run_int_fn(compiled, expected=0, fn_name="negative")
    run_int_fn(compiled, expected=510, fn_name="non_static")


def test_static_size(validate):
    module = GuppyModule("test")

    @guppy(module)
    def negative() -> SizedIter[Range, 10]:
        return range(10)

    validate(module.compile())


def test_py_size(validate):
    module = GuppyModule("test")
    n = 10

    @guppy(module)
    def negative() -> SizedIter[Range, 10]:
        return range(py(n))

    validate(module.compile())


def test_static_generic_size(validate):
    module = GuppyModule("test")
    n = guppy.nat_var("n", module=module)

    @guppy(module)
    def negative() -> SizedIter[Range, n]:
        return range(n)

    validate(module.compile())

