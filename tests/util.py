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


def dump_llvm(hugr: Hugr):
    try:
        from execute_llvm import compile_module_to_string

        hugr_json = hugr.serialize()
        llvm_module = compile_module_to_string(hugr_json)
        print(llvm_module)  # noqa: T201

    except ImportError:
        pass
