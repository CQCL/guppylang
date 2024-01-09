import ast
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import NamedTuple

from guppy.ast_util import AstNode
from guppy.gtypes import (
    BoolType,
    FunctionType,
    GuppyType,
    NoneType,
    Subst,
    SumType,
    TupleType,
)


@dataclass
class Variable:
    """Class holding data associated with a variable."""

    name: str
    ty: GuppyType
    defined_at: AstNode | None
    used: AstNode | None


@dataclass
class CallableVariable(ABC, Variable):
    """Abstract base class for global variables that can be called."""

    ty: FunctionType

    @abstractmethod
    def check_call(
        self, args: list[ast.expr], ty: GuppyType, node: AstNode, ctx: "Context"
    ) -> tuple[ast.expr, Subst]:
        """Checks the return type of a function call against a given type."""

    @abstractmethod
    def synthesize_call(
        self, args: list[ast.expr], node: AstNode, ctx: "Context"
    ) -> tuple[ast.expr, GuppyType]:
        """Synthesizes the return type of a function call."""


@dataclass
class TypeVarDecl:
    """A declared type variable."""

    name: str
    linear: bool


class Globals(NamedTuple):
    """Collection of names that are available on module-level.

    Separately stores names that are bound to values (i.e. module-level functions or
    constants), to types, or to instance functions belonging to types.
    """

    values: dict[str, Variable]
    types: dict[str, type[GuppyType]]
    type_vars: dict[str, TypeVarDecl]

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
        return Globals({}, tys, {})

    def get_instance_func(self, ty: GuppyType, name: str) -> CallableVariable | None:
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
            self.type_vars | other.type_vars,
        )

    def __ior__(self, other: "Globals") -> "Globals":  # noqa: PYI034
        self.values.update(other.values)
        self.types.update(other.types)
        self.type_vars.update(other.type_vars)
        return self


# Local variable mapping
Locals = dict[str, Variable]


class Context(NamedTuple):
    """The type checking context."""

    globals: Globals
    locals: Locals


def qualified_name(ty: type[GuppyType] | str, name: str) -> str:
    """Returns a qualified name for an instance function on a type."""
    ty_name = ty if isinstance(ty, str) else ty.name
    return f"{ty_name}.{name}"
