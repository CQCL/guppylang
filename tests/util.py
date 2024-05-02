import guppylang
from guppylang.hugr_builder.hugr import Hugr
from guppylang.module import GuppyModule


def compile_guppy(fn) -> Hugr:
    """A decorator that combines @guppy with HUGR compilation.

    Creates a temporary module that only contains the defined function.
    """
    assert not isinstance(
        fn,
        GuppyModule,
    ), "`@compile_guppy` does not support extra arguments."

    module = GuppyModule("module")
    guppylang.decorator.guppy(module)(fn)
    return module.compile()
