import ast
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import NamedTuple, Optional, Union

from guppy.ast_util import AstNode
from guppy.guppy_types import GuppyType, FunctionType, TupleType, SumType, NoneType, \
    BoolType


@dataclass
class Variable:
    """Class holding data associated with a variable."""

    name: str
    ty: GuppyType
    defined_at: Optional[AstNode]
    used: Optional[AstNode]


@dataclass
class CallableVariable(ABC, Variable):
    """Abstract base class for global variables that can be called."""

    ty: FunctionType

    @abstractmethod
    def check_call(self, args: list[ast.expr], ty: GuppyType, node: AstNode, ctx: "Context") -> ast.expr:
        """Checks the return type of a function call against a given type."""

    @abstractmethod
    def synthesize_call(self, args: list[ast.expr], node: AstNode, ctx: "Context") -> tuple[ast.expr, GuppyType]:
        """Synthesizes the return type of a function call."""


class Globals(NamedTuple):
    """Collection of names that are available on module-level.

    Separately stores names that are bound to values (i.e. module-level functions or
    constants), to types, or to instance functions belonging to types.
    """

    values: dict[str, Variable]
    types: dict[str, type[GuppyType]]

    @staticmethod
    def default() -> "Globals":
        """Generates a `Globals` instance that is populated with all core types"""
        tys: dict[str, type[GuppyType]] = {
            FunctionType.name: FunctionType,
            TupleType.name: TupleType,
            SumType.name: SumType,
            NoneType.name: NoneType,
            BoolType.name: BoolType,
        }
        return Globals({}, tys)

    def get_instance_func(self, ty: GuppyType, name: str) -> Optional[CallableVariable]:
        """Looks up an instance function with a given name for a type.

        Returns `None` if the name doesn't exist or isn't a function.
        """
        qualname = qualified_name(ty.__class__, name)
        if qualname in self.values:
            val = self.values[qualname]
            if isinstance(val, CallableVariable):
                return val
        return None

    def __or__(self, other: "Globals") -> "Globals":
        return Globals(
            self.values | other.values,
            self.types | other.types,
        )

    def __ior__(self, other: "Globals") -> "Globals":
        self.values.update(other.values)
        self.types.update(other.types)
        return self


# Local variable mapping
Locals = dict[str, Variable]


class Context(NamedTuple):
    """The type checking context."""

    globals: Globals
    locals: Locals


def qualified_name(ty: Union[type[GuppyType], str], name: str) -> str:
    """Returns a qualified name for an instance function on a type."""
    ty_name = ty if isinstance(ty, str) else ty.name
    return f"{ty_name}.{name}"
