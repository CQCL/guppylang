# dump json schema to a directory
# usage: python generate_schema.py <OUT_DIR>
import json
import sys
from pathlib import Path

from pydantic import TypeAdapter

from guppy.hugr.raw import RawHugr

if __name__ == "__main__":
    out_dir = Path(sys.argv[-1])

    with (out_dir / "hugr_schema_v0.json").open("w") as f:
        json.dump(TypeAdapter(RawHugr).json_schema(), f)
