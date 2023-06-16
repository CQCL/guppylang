from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Any

import guppy.hugr.tys as tys


class GuppyType(ABC):
    @abstractmethod
    def to_hugr(self) -> tys.SimpleType:
        pass


@dataclass(frozen=True)
class TypeRow:
    tys: list[GuppyType]

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

    def to_hugr(self) -> tys.SimpleType:
        return tys.Int(size=32)  # TODO: Parametrise over size


@dataclass(frozen=True)
class FloatType(GuppyType):
    def __str__(self) -> str:
        return "float"

    def to_hugr(self) -> tys.SimpleType:
        return tys.F64()


@dataclass(frozen=True)
class BoolType(GuppyType):
    def __str__(self) -> str:
        return "bool"

    def to_hugr(self) -> tys.SimpleType:
        # Hugr bools are encoded as Sum((), ())
        unit = tys.Tuple(tys=[], linear=False)
        s = tys.Sum(tys=list([unit, unit]), linear=False)
        return s


@dataclass(frozen=True)
class FunctionType(GuppyType):
    args: list[GuppyType]
    returns: list[GuppyType]
    arg_names: Optional[list[str]] = None

    def __str__(self) -> str:
        return f"{TypeRow(self.args)} -> {TypeRow(self.returns)}"

    def to_hugr(self) -> tys.SimpleType:
        ins = list([t.to_hugr() for t in self.args])
        outs = list([t.to_hugr() for t in self.returns])
        sig = tys.Signature(input=ins, output=outs, const_input=list([]))
        # TODO: Resources
        return tys.Graph(resources=[], signature=sig)


@dataclass(frozen=True)
class TupleType(GuppyType):
    element_types: list[GuppyType]

    def __str__(self) -> str:
        return f"({', '.join(str(e) for e in self.element_types)})"

    def to_hugr(self) -> tys.SimpleType:
        ts = [t.to_hugr() for t in self.element_types]
        # As soon as one element is linear, the whole tuple must be linear
        return tys.Tuple(tys=ts, linear=any(tys.is_linear(t) for t in ts))


@dataclass(frozen=True)
class SumType(GuppyType):
    element_types: list[GuppyType]

    def __str__(self) -> str:
        return f"Sum({', '.join(str(e) for e in self.element_types)})"

    def to_hugr(self) -> tys.SimpleType:
        ts = [t.to_hugr() for t in self.element_types]
        # As soon as one element is linear, the whole sum type must be linear
        return tys.Sum(tys=ts, linear=any(tys.is_linear(t) for t in ts))


@dataclass(frozen=True)
class StringType(GuppyType):
    def __str__(self) -> str:
        return "str"

    def to_hugr(self) -> tys.SimpleType:
        return tys.String()


@dataclass(frozen=True)
class ListType(GuppyType):
    element_type: GuppyType

    def __str__(self) -> str:
        return f"list[{self.element_type}]"

    def to_hugr(self) -> tys.SimpleType:
        t = self.element_type.to_hugr()
        return tys.List(ty=t, linear=tys.is_linear(t))


@dataclass(frozen=True)
class DictType(GuppyType):
    key_type: GuppyType
    value_type: GuppyType

    def __str__(self) -> str:
        return f"dict[{self.key_type}, {self.value_type}]"

    def to_hugr(self) -> tys.SimpleType:
        kt = self.key_type.to_hugr()
        vt = self.value_type.to_hugr()
        assert not tys.is_linear(kt)
        return tys.Map(key=kt, value=vt, linear = tys.is_linear(vt))


def type_from_python_value(val: Any) -> Optional[GuppyType]:
    """ Checks if the given Python value is a valid Guppy value.
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
