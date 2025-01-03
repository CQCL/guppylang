from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.option import Option, nothing, some


def test_none(validate, run_int_fn):
    module = GuppyModule("test_range")
    module.load(Option, nothing)

    @guppy(module)
    def main() -> int:
        x: Option[int] = nothing()
        is_none = 10 if x.is_nothing() else 0
        is_some = 1 if x.is_some() else 0
        return is_none + is_some

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=10)


def test_some_unwrap(validate, run_int_fn):
    module = GuppyModule("test_range")
    module.load(Option, some)

    @guppy(module)
    def main() -> int:
        x: Option[int] = some(42)
        is_none = 1 if x.is_nothing() else 0
        is_some = x.unwrap() if x.is_some() else 0
        return is_none + is_some

    compiled = module.compile()
    validate(compiled)
    run_int_fn(compiled, expected=42)

