from dataclasses import dataclass

from hugr import val
from tket_exts import (
    debug,
    futures,
    gpu,
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
QSYSTEM_GPU_EXTENSION = gpu()
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
    QSYSTEM_GPU_EXTENSION,
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

    def to_value(self) -> val.Extension:
        ty = WASM_EXTENSION.get_type("module").instantiate([])

        name = "tket.wasm.module"
        payload = {"module_filename": self.wasm_file}
        return val.Extension(name, typ=ty, val=payload, extensions=["tket.wasm"])

    def __str__(self) -> str:
        return (
            f"tket.wasm.module(module_filename={self.wasm_file})"
        )

@dataclass(frozen=True)
class ConstGpuModule(val.ExtensionValue):
    """Python wrapper for the tket ConstWasmModule type"""

    gpu_file: str
    gpu_config: str | None

    def to_value(self) -> val.Extension:
        ty = QSYSTEM_GPU_EXTENSION.get_type("module").instantiate([])

        name = "ConstGpuModule"
        payload = {
            "module_filename": self.gpu_file,
            "config_filename": self.gpu_config,
        }
        return val.Extension(name, typ=ty, val=payload, extensions=["tket.gpu"])

    def __str__(self) -> str:
        return (
            f"tket.gpu.module(gpu_file={self.gpu_file}, gpu_config={self.gpu_config})"
        )
