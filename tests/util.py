from __future__ import annotations

from typing import TYPE_CHECKING

import guppylang
from guppylang import guppy

if TYPE_CHECKING:
    from hugr.package import FuncDefnPointer, PackagePointer


def compile_guppy(fn) -> FuncDefnPointer:
    """A decorator that combines @guppy with HUGR compilation."""
    defn = guppylang.decorator.guppy(fn)
    return guppy.compile(defn)


def dump_llvm(package: PackagePointer):
    try:
        from execute_llvm import compile_module_to_string

        llvm_module = compile_module_to_string(package.package.to_bytes())
        print(llvm_module)  # noqa: T201

    except ImportError:
        pass
