import ast
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, NamedTuple

from guppy.ast_util import AstNode, name_nodes_in_ast
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


PyScope = dict[str, Any]


class Globals(NamedTuple):
    """Collection of names that are available on module-level.

    Separately stores names that are bound to values (i.e. module-level functions or
    constants), to types, or to instance functions belonging to types.
    """

    values: dict[str, Variable]
    types: dict[str, type[GuppyType]]
    type_vars: dict[str, TypeVarDecl]
    python_scope: PyScope

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
        return Globals({}, tys, {}, {})

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
            self.python_scope | other.python_scope,
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


class DummyEvalDict(PyScope):
    """A custom dict that can be passed to `eval` to give better error messages.
    This class is used to implement the `py(...)` expression. If the user tries to
    access a Guppy variable in the Python context, we give an informative error message.
    """

    ctx: Context
    node: ast.expr

    @dataclass
    class GuppyVarUsedError(BaseException):
        """Error that is raised when the user tries to access a Guppy variable."""

        var: str
        node: ast.Name | None

    def __init__(self, ctx: Context, node: ast.expr):
        super().__init__(**ctx.globals.python_scope)
        self.ctx = ctx
        self.node = node

    def _check_item(self, key: str) -> None:
        # Catch the user trying to access Guppy variables
        if key in self.ctx.locals:
            # Find the name node in the AST where the usage occurs
            n = next((n for n in name_nodes_in_ast(self.node) if n.id == key), None)
            raise self.GuppyVarUsedError(key, n)

    def __getitem__(self, key: str) -> Any:
        self._check_item(key)
        return super().__getitem__(key)

    def __delitem__(self, key: str) -> None:
        self._check_item(key)
        super().__delitem__(key)

    def __contains__(self, key: object) -> bool:
        if isinstance(key, str) and key in self.ctx.locals:
            return True
        return super().__contains__(key)


def qualified_name(ty: type[GuppyType] | str, name: str) -> str:
    """Returns a qualified name for an instance function on a type."""
    ty_name = ty if isinstance(ty, str) else ty.name
    return f"{ty_name}.{name}"
