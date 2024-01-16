from typing import Any, Literal

import ormsgpack
from pydantic import BaseModel

from guppy.hugr.ops import NodeID, OpType

Port = tuple[NodeID, int | None]  # (node, offset)
Edge = tuple[Port, Port]


class RawHugr(BaseModel):
    version: Literal["v0"] = "v0"
    nodes: list[OpType]
    edges: list[Edge]

    def packb(self) -> bytes:
        return ormsgpack.packb(self.model_dump(), option=ormsgpack.OPT_NON_STR_KEYS)

    def to_json(self) -> str:
        """Return a JSON representation of the Hugr."""
        return self.model_dump_json()

    @classmethod
    def unpackb(cls, b: bytes) -> "RawHugr":
        """Decode a msgpack-encoded Hugr."""
        return cls(**ormsgpack.unpackb(b, option=ormsgpack.OPT_NON_STR_KEYS))

    @classmethod
    def load_json(cls, json: dict[Any, Any]) -> "RawHugr":
        """Decode a JSON-encoded Hugr."""
        return cls(**json)
