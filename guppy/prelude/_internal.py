from typing import Literal

from pydantic import BaseModel

from guppy.hugr import val


INT_WIDTH = 6  # 2^6 = 64 bit


class ConstIntS(BaseModel):
    """Hugr representation of signed integers in the arithmetic extension."""

    c: Literal["ConstIntS"] = "ConstIntS"
    log_width: int
    value: int


class ConstF64(BaseModel):
    """Hugr representation of floats in the arithmetic extension."""

    c: Literal["ConstF64"] = "ConstF64"
    value: float


def bool_value(b: bool) -> val.Value:
    """Returns the Hugr representation of a boolean value."""
    return val.Sum(tag=int(b), value=val.Tuple(vs=[]))


def int_value(i: int) -> val.Value:
    """Returns the Hugr representation of an integer value."""
    return val.Prim(val=val.ExtensionVal(c=(ConstIntS(log_width=INT_WIDTH, value=i),)))


def float_value(f: float) -> val.Value:
    """Returns the Hugr representation of a float value."""
    return val.Prim(val=val.ExtensionVal(c=(ConstF64(value=f),)))
