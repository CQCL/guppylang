from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Any, Sequence

import guppy.hugr.tys as tys


class GuppyType(ABC):
    """Base class for all Guppy types.

    Note that all instances of `GuppyType` subclasses are expected to be immutable.
    """

    @property
    @abstractmethod
    def linear(self) -> bool:
        pass

    @abstractmethod
    def to_hugr(self) -> tys.SimpleType:
        pass


@dataclass(frozen=True)
class TypeRow:
    tys: Sequence[GuppyType]

    def __str__(self) -> str:
        if len(self.tys) == 0:
            return "None"
        elif len(self.tys) == 1:
            return str(self.tys[0])
        else:
            return f"({', '.join(str(e) for e in self.tys)})"


@dataclass(frozen=True)
class IntType(GuppyType):
    def __str__(self) -> str:
        return "int"

    @property
    def linear(self) -> bool:
        return False

    def to_hugr(self) -> tys.SimpleType:
        return tys.Int(width=32)  # TODO: Parametrise over size


@dataclass(frozen=True)
class FloatType(GuppyType):
    def __str__(self) -> str:
        return "float"

    @property
    def linear(self) -> bool:
        return False

    def to_hugr(self) -> tys.SimpleType:
        # TODO: Use float type
        return tys.Int(width=32)


@dataclass(frozen=True)
class FunctionType(GuppyType):
    args: Sequence[GuppyType]
    returns: Sequence[GuppyType]
    arg_names: Optional[Sequence[str]] = field(
        default=None,
        compare=False,  # Argument names are not taken into account for type equality
    )

    def __str__(self) -> str:
        return f"{TypeRow(self.args)} -> {TypeRow(self.returns)}"

    @property
    def linear(self) -> bool:
        return False

    def to_hugr(self) -> tys.SimpleType:
        ins = [t.to_hugr() for t in self.args]
        outs = [t.to_hugr() for t in self.returns]
        # TODO: Resources
        return tys.FunctionType(input=ins, output=outs, extension_reqs=[])


@dataclass(frozen=True)
class TupleType(GuppyType):
    element_types: Sequence[GuppyType]

    def __str__(self) -> str:
        return f"({', '.join(str(e) for e in self.element_types)})"

    @property
    def linear(self) -> bool:
        return any(t.linear for t in self.element_types)

    def to_hugr(self) -> tys.SimpleType:
        ts = [t.to_hugr() for t in self.element_types]
        return tys.Tuple(inner=ts)


@dataclass(frozen=True)
class SumType(GuppyType):
    element_types: Sequence[GuppyType]

    def __str__(self) -> str:
        return f"Sum({', '.join(str(e) for e in self.element_types)})"

    @property
    def linear(self) -> bool:
        return any(t.linear for t in self.element_types)

    def to_hugr(self) -> tys.SimpleType:
        if all(
            isinstance(e, TupleType) and len(e.element_types) == 0
            for e in self.element_types
        ):
            return tys.SimpleSum(size=len(self.element_types))
        return tys.GeneralSum(row=[t.to_hugr() for t in self.element_types])


@dataclass(frozen=True)
class BoolType(SumType):
    def __init__(self) -> None:
        # Hugr bools are encoded as Sum((), ())
        super().__init__([TupleType([]), TupleType([])])

    @property
    def linear(self) -> bool:
        return False

    def __str__(self) -> str:
        return "bool"


@dataclass(frozen=True)
class StringType(GuppyType):
    def __str__(self) -> str:
        return "str"

    @property
    def linear(self) -> bool:
        return False

    def to_hugr(self) -> tys.SimpleType:
        return tys.String()


@dataclass(frozen=True)
class QubitType(GuppyType):
    def __str__(self) -> str:
        return "qubit"

    @property
    def linear(self) -> bool:
        return True

    def to_hugr(self) -> tys.SimpleType:
        return tys.Qubit()


@dataclass(frozen=True)
class ListType(GuppyType):
    element_type: GuppyType

    def __str__(self) -> str:
        return f"list[{self.element_type}]"

    @property
    def linear(self) -> bool:
        return self.element_type.linear

    def to_hugr(self) -> tys.SimpleType:
        t = self.element_type.to_hugr()
        return tys.List(ty=t)


def type_from_python_value(val: Any) -> Optional[GuppyType]:
    """Checks if the given Python value is a valid Guppy value.

    In that case, the Guppy type of the value is returned.
    """
    if isinstance(val, bool):
        return BoolType()
    elif isinstance(val, int):
        return IntType()
    elif isinstance(val, float):
        return FloatType()
    elif isinstance(val, str):
        return StringType()
    return None
