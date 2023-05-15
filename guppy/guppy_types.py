from dataclasses import dataclass
from typing import Optional


class GuppyType(object):
    pass


@dataclass(frozen=True)
class RowType(GuppyType):
    element_types: list[GuppyType]

    def __str__(self):
        if len(self.element_types) == 0:
            return "None"
        elif len(self.element_types) == 1:
            return str(self.element_types[0])
        else:
            return f"({', '.join(str(e) for e in self.element_types)})"


@dataclass(frozen=True)
class IntType(GuppyType):
    def __str__(self):
        return "int"


@dataclass(frozen=True)
class FloatType(GuppyType):
    def __str__(self):
        return "float"


@dataclass(frozen=True)
class BoolType(GuppyType):
    def __str__(self):
        return "bool"


@dataclass(frozen=True)
class FunctionType(GuppyType):
    args: list[GuppyType]
    returns: list[GuppyType]
    arg_names: list[str]

    def __str__(self):
        return f"{RowType(self.args)} -> {RowType(self.returns)}"


@dataclass(frozen=True)
class TupleType(GuppyType):
    element_types: list[GuppyType]

    def __str__(self):
        return f"({', '.join(str(e) for e in self.element_types)})"


@dataclass(frozen=True)
class StringType(GuppyType):
    def __str__(self):
        return "str"


@dataclass(frozen=True)
class ListType(GuppyType):
    element_type: GuppyType

    def __str__(self):
        return f"list[{self.element_type}]"


@dataclass(frozen=True)
class SetType(GuppyType):
    element_type: GuppyType

    def __str__(self):
        return f"set[{self.element_type}]"


@dataclass(frozen=True)
class DictType(GuppyType):
    key_type: GuppyType
    value_type: GuppyType

    def __str__(self):
        return f"dct[{self.key_type}, {self.value_type}]"


@dataclass(frozen=True)
class TypeVar(GuppyType):
    name: str


def type_from_python_value(val: object) -> Optional[GuppyType]:
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

