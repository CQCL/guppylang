from typing import Literal

import ormsgpack

from guppy.hugr.pydantic_extensions import BaseModel
from guppy.hugr.ops import OpType


NodeID = int
Node = tuple[NodeID, int, int]  # (parent, #incoming, #outgoing)
Port = tuple[NodeID, int]  # (node, offset)
Edge = tuple[Port, Port]


class RawHugr(BaseModel):
    version: Literal["v0"] = "v0"
    nodes: list[Node]
    edges: list[Edge]
    root: NodeID
    op_types: dict[NodeID, OpType]

    def packb(self) -> bytes:
        return ormsgpack.packb(self.dict(), option=ormsgpack.OPT_NON_STR_KEYS)

    @classmethod
    def unpackb(cls, b: bytes) -> "RawHugr":
        return cls(**ormsgpack.unpackb(b, option=ormsgpack.OPT_NON_STR_KEYS))
