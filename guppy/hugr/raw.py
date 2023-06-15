from typing import Literal, Optional

import ormsgpack

from guppy.hugr.pydantic_extensions import BaseModel
from guppy.hugr.ops import OpType


NodeID = int
Node = tuple[NodeID,  OpType]  # (parent, optype)
Port = tuple[NodeID, Optional[int]]  # (node, offset)
Edge = tuple[Port, Port]


class RawHugr(BaseModel):
    version: Literal["v0"] = "v0"
    nodes: list[Node]
    edges: list[Edge]

    def packb(self) -> bytes:
        return ormsgpack.packb(self.dict(), option=ormsgpack.OPT_NON_STR_KEYS)

    @classmethod
    def unpackb(cls, b: bytes) -> "RawHugr":
        return cls(**ormsgpack.unpackb(b, option=ormsgpack.OPT_NON_STR_KEYS))
