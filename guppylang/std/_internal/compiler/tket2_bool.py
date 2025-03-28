from dataclasses import dataclass

from hugr import ops
from hugr import tys as ht
from hugr import val as hv

from guppylang.std._internal.compiler.tket2_exts import BOOL_EXTENSION

BOOL_DEF = BOOL_EXTENSION.get_type("bool")
OpaqueBool = ht.ExtType(BOOL_DEF)


def bool_to_sum() -> ops.ExtOp:
    return ops.ExtOp(
        BOOL_EXTENSION.get_op("bool_to_sum"),
        ht.FunctionType([OpaqueBool], [ht.Bool]),
    )


def sum_to_bool() -> ops.ExtOp:
    return ops.ExtOp(
        BOOL_EXTENSION.get_op("sum_to_bool"),
        ht.FunctionType([ht.Bool], [OpaqueBool]),
    )


def not_op() -> ops.ExtOp:
    return ops.ExtOp(
        BOOL_EXTENSION.get_op("not"),
        ht.FunctionType([OpaqueBool], [OpaqueBool]),
    )


@dataclass
class OpaqueBoolVal(hv.ExtensionValue):
    """Custom value for a boolean."""

    v: bool

    def to_value(self) -> hv.Extension:
        name = "ConstBool"
        payload = self.v
        return hv.Extension(
            name,
            typ=OpaqueBool,
            val=payload,
            extensions=[BOOL_EXTENSION.name],
        )

    def __str__(self) -> str:
        return f"{self.v}"
