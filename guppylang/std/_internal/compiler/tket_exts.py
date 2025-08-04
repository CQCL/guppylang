from dataclasses import dataclass

from hugr import val
from tket_exts import (
    debug,
    futures,
    opaque_bool,
    qsystem,
    qsystem_random,
    qsystem_utils,
    quantum,
    result,
    rotation,
    wasm,
)

BOOL_EXTENSION = opaque_bool()
DEBUG_EXTENSION = debug()
FUTURES_EXTENSION = futures()
QSYSTEM_EXTENSION = qsystem()
QSYSTEM_RANDOM_EXTENSION = qsystem_random()
QSYSTEM_UTILS_EXTENSION = qsystem_utils()
QUANTUM_EXTENSION = quantum()
RESULT_EXTENSION = result()
ROTATION_EXTENSION = rotation()
WASM_EXTENSION = wasm()

TKET_EXTENSIONS = [
    BOOL_EXTENSION,
    DEBUG_EXTENSION,
    FUTURES_EXTENSION,
    QSYSTEM_EXTENSION,
    QSYSTEM_RANDOM_EXTENSION,
    QSYSTEM_UTILS_EXTENSION,
    QUANTUM_EXTENSION,
    RESULT_EXTENSION,
    ROTATION_EXTENSION,
    WASM_EXTENSION,
]


@dataclass(frozen=True)
class ConstWasmModule(val.ExtensionValue):
    """Python wrapper for the tket ConstWasmModule type"""

    wasm_file: str
    wasm_hash: int

    def to_value(self) -> val.Extension:
        ty = WASM_EXTENSION.get_type("module").instantiate([])

        name = "tket.wasm.ConstWasmModule"
        payload = {"name": self.wasm_file, "hash": self.wasm_hash}
        return val.Extension(name, typ=ty, val=payload, extensions=["tket.wasm"])

    def __str__(self) -> str:
        return (
            f"ConstWasmModule(wasm_file={self.wasm_file}, wasm_hash={self.wasm_hash})"
        )
