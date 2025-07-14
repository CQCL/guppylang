from __future__ import annotations

from typing import TYPE_CHECKING

import guppylang
from guppylang import guppy
from guppylang.decorator import custom_guppy_decorator

if TYPE_CHECKING:
    from hugr.package import FuncDefnPointer, PackagePointer


@custom_guppy_decorator
def compile_guppy(fn) -> FuncDefnPointer:
    """A decorator that combines @guppy with HUGR compilation."""
    defn = guppylang.decorator.guppy(fn)
    return guppy.compile(defn)


def dump_llvm(package: PackagePointer):
    try:
        from selene_hugr_qis_compiler import compile_to_llvm_ir

        llvm_module = compile_to_llvm_ir(package.package.to_bytes())
        print(llvm_module)  # noqa: T201

    except ImportError:
        pass
