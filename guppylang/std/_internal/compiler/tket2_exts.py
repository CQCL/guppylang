from dataclasses import dataclass

import hugr.model
import hugr.std
from hugr import val
from tket2_exts import (
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
GPU_EXTENSION = gpu()
QSYSTEM_EXTENSION = qsystem()
QSYSTEM_GPU_EXTENSION = gpu()
QSYSTEM_RANDOM_EXTENSION = qsystem_random()
QSYSTEM_UTILS_EXTENSION = qsystem_utils()
QUANTUM_EXTENSION = quantum()
RESULT_EXTENSION = result()
ROTATION_EXTENSION = rotation()
WASM_EXTENSION = wasm()

TKET2_EXTENSIONS = [
    BOOL_EXTENSION,
    DEBUG_EXTENSION,
    FUTURES_EXTENSION,
    GPU_EXTENSION,
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
    """Python wrapper for the tket2 ConstWasmModule type"""

    wasm_file: str
    wasm_hash: int

    def to_value(self) -> val.Extension:
        ty = WASM_EXTENSION.get_type("module").instantiate([])

        name = "tket2.wasm.ConstWasmModule"
        payload = {"name": self.wasm_file, "hash": self.wasm_hash}
        return val.Extension(name, typ=ty, val=payload, extensions=["tket2.wasm"])

    def __str__(self) -> str:
        return (
            f"ConstWasmModule(wasm_file={self.wasm_file}, wasm_hash={self.wasm_hash})"
        )

    def to_model(self) -> hugr.model.Term:
        file_tm = hugr.model.Literal(self.wasm_file)
        hash_tm = hugr.model.Literal(self.wasm_hash)

        return hugr.model.Apply("tket2.wasm.ConstWasmModule", [file_tm, hash_tm])

@dataclass(frozen=True)
class ConstGpuModule(val.ExtensionValue):
    """Python wrapper for the tket2 ConstWasmModule type"""

    gpu_file: str
    gpu_hash: int
    gpu_config: str | None

    def to_value(self) -> val.Extension:
        ty = WASM_EXTENSION.get_type("module").instantiate([])

        name = "tket2.wasm.ConstWasmModule"
        payload = {"name": self.gpu_file, "hash": self.gpu_hash, "config": self.gpu_config}
        return val.Extension(name, typ=ty, val=payload, extensions=["tket2.wasm"])

    def __str__(self) -> str:
        return (
            f"ConstGpuModule(gpu_file={self.gpu_file}, gpu_hash={self.gpu_hash}, gpu_config={self.gpu_config})"
        )

    def to_model(self) -> hugr.model.Term:
        file_tm = hugr.model.Literal(self.gpu_file)
        hash_tm = hugr.model.Literal(self.gpu_hash)
        if isinstance(self.gpu_config, str):
            config_tm = hugr.val.Some(hugr.std.prelude.StringVal(self.gpu_config)).to_model()
        else:
            config_tm = hugr.val.None_().to_model()

        return hugr.model.Apply("tket2.gpu.ConstGpuModule", [file_tm, hash_tm, config_tm])
