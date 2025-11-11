from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from guppylang.decorator import custom_guppy_decorator, guppy

if TYPE_CHECKING:
    from hugr.package import Package, PackagePointer

    from guppylang.defs import GuppyFunctionDefinition


@custom_guppy_decorator
def compile_guppy(fn) -> Package:
    """A decorator that combines @guppy with HUGR compilation."""
    defn: GuppyFunctionDefinition = guppy(fn)
    return defn.compile_function()


def dump_llvm(package: PackagePointer):
    try:
        from selene_hugr_qis_compiler import compile_to_llvm_ir

        llvm_module = compile_to_llvm_ir(package.package.to_bytes())
        print(llvm_module)  # noqa: T201

    except ImportError:
        pass


def get_wasm_file() -> str:
    return Path(__file__).parent.resolve() / "resources/arith.wasm"
