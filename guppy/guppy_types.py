from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Any

import guppy.hugr.tys as tys


class GuppyType(ABC):
    @abstractmethod
    def to_hugr(self) -> tys.SimpleType:
        pass

    @abstractmethod
    def clone(self) -> "GuppyType":
        pass


@dataclass(frozen=True)
class RowType(GuppyType):
    element_types: list[GuppyType]

    def __str__(self) -> str:
        if len(self.element_types) == 0:
            return "None"
        elif len(self.element_types) == 1:
            return str(self.element_types[0])
        else:
            return f"({', '.join(str(e) for e in self.element_types)})"

    def to_hugr(self) -> tys.SimpleType:
        raise NotImplementedError()
        # return tys.TypeRow(types=[t.to_hugr() for t in self.element_types])

    def clone(self) -> "RowType":
        return RowType([t.clone() for t in self.element_types])


@dataclass(frozen=True)
class IntType(GuppyType):
    def __str__(self) -> str:
        return "int"

    def to_hugr(self) -> tys.SimpleType:
        return tys.Classic(ty=tys.Int(size=32))  # TODO: Parametrise over size

    def clone(self) -> "IntType":
        return IntType()


@dataclass(frozen=True)
class FloatType(GuppyType):
    def __str__(self) -> str:
        return "float"

    def to_hugr(self) -> tys.SimpleType:
        return tys.Classic(ty=tys.F64())

    def clone(self) -> "FloatType":
        return FloatType()


@dataclass(frozen=True)
class BoolType(GuppyType):
    def __str__(self) -> str:
        return "bool"

    def to_hugr(self) -> tys.SimpleType:
        # Hugr bools are encoded as Sum((), ())
        unit = tys.Classic(ty=tys.ContainerClassic(ty=tys.Tuple(tys=tys.TypeRow(types=[]))))
        s = tys.Sum(tys=tys.TypeRow(types=[unit, unit]))
        return tys.Classic(ty=tys.ContainerClassic(ty=s))

    def clone(self) -> "BoolType":
        return BoolType()


@dataclass(frozen=True)
class FunctionType(GuppyType):
    args: list[GuppyType]
    returns: list[GuppyType]
    arg_names: Optional[list[str]] = None

    def __str__(self) -> str:
        return f"{RowType(self.args)} -> {RowType(self.returns)}"

    def to_hugr(self) -> tys.SimpleType:
        ins = tys.TypeRow(types=[t.to_hugr() for t in self.args])
        outs = tys.TypeRow(types=[t.to_hugr() for t in self.returns])
        sig = tys.Signature(input=ins, output=outs, const_input=tys.TypeRow(types=[]))
        # TODO: Resources
        return tys.Classic(ty=tys.Graph(resources=[], signature=sig))

    def clone(self) -> "FunctionType":
        return FunctionType([t.clone() for t in self.args], [t.clone() for t in self.returns],
                            self.arg_names.copy() if self.arg_names is not None else None)


@dataclass(frozen=True)
class TupleType(GuppyType):
    element_types: list[GuppyType]

    def __str__(self) -> str:
        return f"({', '.join(str(e) for e in self.element_types)})"

    def to_hugr(self) -> tys.SimpleType:
        ts = [t.to_hugr() for t in self.element_types]
        # As soon as one element is linear, the whole tuple must be linear
        if any(isinstance(t, tys.Linear) for t in ts):
            return tys.Linear(ty=tys.ContainerLinear(ty=tys.Tuple(tys=tys.TypeRow(types=ts))))
        else:
            return tys.Classic(ty=tys.ContainerClassic(ty=tys.Tuple(tys=tys.TypeRow(types=ts))))

    def clone(self) -> "TupleType":
        return TupleType([t.clone() for t in self.element_types])


@dataclass(frozen=True)
class SumType(GuppyType):
    element_types: list[GuppyType]

    def __str__(self) -> str:
        return f"Sum({', '.join(str(e) for e in self.element_types)})"

    def to_hugr(self) -> tys.SimpleType:
        ts = [t.to_hugr() for t in self.element_types]
        # As soon as one element is linear, the whole sum type must be linear
        if any(isinstance(t, tys.Linear) for t in ts):
            return tys.Linear(ty=tys.ContainerLinear(ty=tys.Sum(tys=tys.TypeRow(types=ts))))
        else:
            return tys.Classic(ty=tys.ContainerClassic(ty=tys.Sum(tys=tys.TypeRow(types=ts))))

    def clone(self) -> "SumType":
        return SumType([t.clone() for t in self.element_types])


@dataclass(frozen=True)
class StringType(GuppyType):
    def __str__(self) -> str:
        return "str"

    def to_hugr(self) -> tys.SimpleType:
        return tys.Classic(ty=tys.String())

    def clone(self) -> "StringType":
        return StringType()


@dataclass(frozen=True)
class ListType(GuppyType):
    element_type: GuppyType

    def __str__(self) -> str:
        return f"list[{self.element_type}]"

    def to_hugr(self) -> tys.SimpleType:
        t = self.element_type.to_hugr()
        if isinstance(t, tys.Linear):
            return tys.Linear(ty=tys.ContainerLinear(ty=tys.ListLinear(ty=t.ty)))
        else:
            return tys.Classic(ty=tys.ContainerClassic(ty=tys.ListClassic(ty=t.ty)))

    def clone(self) -> "ListType":
        return ListType(self.element_type.clone())


@dataclass(frozen=True)
class SetType(GuppyType):
    element_type: GuppyType

    def __str__(self) -> str:
        return f"set[{self.element_type}]"

    def to_hugr(self) -> tys.SimpleType:
        # Not yet available in Hugr
        raise NotImplementedError()

    def clone(self) -> "SetType":
        return SetType(self.element_type.clone())


@dataclass(frozen=True)
class DictType(GuppyType):
    key_type: GuppyType
    value_type: GuppyType

    def __str__(self) -> str:
        return f"dict[{self.key_type}, {self.value_type}]"

    def to_hugr(self) -> tys.SimpleType:
        # Not yet available in Hugr
        raise NotImplementedError()

    def clone(self) -> "DictType":
        return DictType(self.key_type.clone(), self.value_type.clone())


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
