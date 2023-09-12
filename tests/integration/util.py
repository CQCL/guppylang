from typing import TypeVar
import os
from pathlib import Path

import validator
from guppy.hugr.hugr import Hugr
from guppy.compiler import GuppyModule

def export_hugr(hugr: bytes, name: str):
    export_dir = os.environ.get("GUPPY_TEST_EXPORT_PATH");
    if(export_dir):
        export_path = Path(export_dir) / f"{name}.msgpack"
        export_path.write_bytes(hugr)

def validate(hugr: Hugr, name = None):
    raw = hugr.serialize()
    if name:
        export_hugr(raw, name)
    validator.validate(raw)

def validate_module(module: GuppyModule, exit_on_error=True):
    hugr: Hugr = module.compile(exit_on_error=exit_on_error)
    return validate(hugr, module.name)

class Decorator:
    def __matmul__(self, other):
        return None


# Dummy names to import to avoid errors for `_@functional` pseudo-decorator:
functional = Decorator()
_ = Decorator()

qubit = TypeVar("qubit")
