from typing import Any, Literal

from pydantic import BaseModel

from guppylang.hugr.ops import NodeID, OpType

Port = tuple[NodeID, int | None]  # (node, offset)
Edge = tuple[Port, Port]


class RawHugr(BaseModel):
    version: Literal["v0"] = "v0"
    nodes: list[OpType]
    edges: list[Edge]

    def to_json(self) -> str:
        """Return a JSON representation of the Hugr."""
        return self.model_dump_json()

    @classmethod
    def load_json(cls, json: dict[Any, Any]) -> "RawHugr":
        """Decode a JSON-encoded Hugr."""
        return cls(**json)
