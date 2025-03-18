from __future__ import annotations

from typing import TYPE_CHECKING

import guppylang
from guppylang.module import GuppyModule

if TYPE_CHECKING:
    from hugr.package import FuncDefnPointer, PackagePointer


def compile_guppy(fn) -> FuncDefnPointer:
    """A decorator that combines @guppy with HUGR compilation.

    Creates a temporary module that only contains the defined function.
    """
    assert not isinstance(
        fn,
        GuppyModule,
    ), "`@compile_guppy` does not support extra arguments."

    module = GuppyModule("module")
    defn = guppylang.decorator.guppy(module)(fn)
    return defn.compile()


def dump_llvm(package: PackagePointer):
    try:
        from execute_llvm import compile_module_to_string

        llvm_module = compile_module_to_string(package.package.to_bytes())
        print(llvm_module)  # noqa: T201

    except ImportError:
        pass
