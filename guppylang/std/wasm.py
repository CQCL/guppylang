# mypy: disable-error-code="no-any-return"
from typing import no_type_check

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std._internal.compiler.quantum import (
    WASM_EXTENSION,
    WASMCONTEXT_T,
)
from guppylang.std._internal.util import external_op
from guppylang.std.builtins import owned, panic
from guppylang.std.option import Option

wasm = GuppyModule("wasm")


@guppy.hugr_op(
    external_op("get_context", [], ext=WASM_EXTENSION),
    module=wasm,
)
@no_type_check
def _get_context(id: int) -> Option["WASMContext"]: ...


@guppy.type(WASMCONTEXT_T, copyable=False, droppable=True, module=wasm)
class WASMContext:
    """Affine type representing state of environment."""

    @guppy(wasm)  # type: ignore[misc] # Self argument missing for a non-static method (or an invalid type for self)
    def __new__(id: int) -> "WASMContext":
        """Returns a new WASM environment."""
        return _get_context(id).unwrap()

    @guppy(wasm)
    def discard(self: "WASMContext" @ owned) -> None:  # type: ignore[valid-type] # Invalid type comment or annotation
        """Discard the wasm environment."""
        self._dispose_context()

    @guppy.hugr_op(
        external_op("dispose_context", [], ext=WASM_EXTENSION),
        module=wasm,
    )
    @no_type_check
    def _dispose_context(self: "WASMContext" @ owned) -> None: ...

    # TODO:
    # 1. lookup and call for user-provided wasm functions
    # 2. load a user-provided wasm module?


@no_type_check
def new_wasm_checked() -> Option[WASMContext]:
    """Returns a new WASM environment if available else None."""
    # TODO: figure out how to get the id
    return _get_context(0)


@no_type_check
def new_wasm() -> WASMContext:
    """Panicking version of `new_wasm_checked`"""
    wasm = new_wasm_checked()
    if wasm.is_some():
        return wasm.unwrap()
    panic("No more WASM environments available")
