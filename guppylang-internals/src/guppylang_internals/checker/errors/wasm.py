from dataclasses import dataclass
from typing import ClassVar

from guppylang_internals.diagnostic import Error
from guppylang_internals.tys.ty import Type


@dataclass(frozen=True)
class WasmError(Error):
    title: ClassVar[str] = "WASM signature error"


@dataclass(frozen=True)
class FirstArgNotModule(WasmError):
    span_label: ClassVar[str] = (
        "First argument to WASM function should be a reference to a WASM module."
        " Found `{ty}` instead"
    )
    ty: Type


@dataclass(frozen=True)
class UnWasmableType(WasmError):
    span_label: ClassVar[str] = (
        "WASM function signature contained an unsupported type: `{ty}`"
    )
    ty: Type


@dataclass(frozen=True)
class WasmTypeConversionError(Error):
    title: ClassVar[str] = "Can't convert type to WASM"
    span_label: ClassVar[str] = "`{thing}` cannot be converted to WASM"
    ty: Type
