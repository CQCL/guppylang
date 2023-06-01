import subprocess
from pathlib import Path

from guppy.hugr.hugr import Hugr


VALIDATOR_PATH = Path("validator/target/release/validator")


def validate(hugr: Hugr, tmp_path: Path):
    p = tmp_path / "test.hugr"
    with open(p, "wb") as f:
        f.write(hugr.serialize())
    proc = subprocess.run([VALIDATOR_PATH, p])
    assert proc.returncode == 0, "Validation failed:\n" + str(proc.stderr)
