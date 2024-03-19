import ast
import copy
import itertools
from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any, NamedTuple

from typing_extensions import assert_never

from guppylang.ast_util import AstNode, name_nodes_in_ast
from guppylang.tys.definition import TypeDef, callable_type_def, list_type_def, \
    tuple_type_def, none_type_def, linst_type_def, bool_type_def
from guppylang.tys.param import Parameter
from guppylang.tys.subst import Subst
from guppylang.tys.ty import (
    FunctionType,
    GuppyType,
    NoneType,
    TupleType, BoundTypeVar, ExistentialTypeVar, OpaqueType, SumType,
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
    type_defs: dict[str, TypeDef]
    param_vars: dict[str, Parameter]
    python_scope: PyScope

    @staticmethod
    def default() -> "Globals":
        """Generates a `Globals` instance that is populated with all core types"""
        type_defs = {
            "Callable": callable_type_def,
            "tuple": tuple_type_def,
            "None": none_type_def,
            "bool": bool_type_def,
            "list": list_type_def,
            "linst": linst_type_def,
        }
        return Globals({}, type_defs, {}, {})

    def get_instance_func(self, ty: GuppyType, name: str) -> CallableVariable | None:
        """Looks up an instance function with a given name for a type.

        Returns `None` if the name doesn't exist or isn't a function.
        """
        defn: TypeDef
        match ty:
            case BoundTypeVar() | ExistentialTypeVar() | SumType():
                return None
            case FunctionType():
                defn = callable_type_def
            case OpaqueType() as ty:
                defn = ty.defn
            case TupleType():
                defn = tuple_type_def
            case NoneType():
                defn = none_type_def
            case _:
                assert_never(ty)

        qualname = qualified_name(defn.name, name)
        if qualname in self.values:
            val = self.values[qualname]
            if isinstance(val, CallableVariable):
                return val
        return None

    def __or__(self, other: "Globals") -> "Globals":
        return Globals(
            self.values | other.values,
            self.type_defs | other.type_defs,
            self.param_vars | other.param_vars,
            self.python_scope | other.python_scope,
        )

    def __ior__(self, other: "Globals") -> "Globals":  # noqa: PYI034
        self.values.update(other.values)
        self.type_defs.update(other.type_defs)
        self.param_vars.update(other.param_vars)
        return self


@dataclass
class Locals:
    """Scoped mapping from names to variables"""

    vars: dict[str, Variable]
    parent_scope: "Locals | None" = None

    def __getitem__(self, item: str) -> Variable:
        if item not in self.vars and self.parent_scope:
            return self.parent_scope[item]

        return self.vars[item]

    def __setitem__(self, key: str, value: Variable) -> None:
        self.vars[key] = value

    def __iter__(self) -> Iterator[str]:
        parent_iter = iter(self.parent_scope) if self.parent_scope else iter(())
        return itertools.chain(iter(self.vars), parent_iter)

    def __contains__(self, item: str) -> bool:
        return (item in self.vars) or (
            self.parent_scope is not None and item in self.parent_scope
        )

    def __copy__(self) -> "Locals":
        # Make a copy of the var map so that mutating the copy doesn't
        # mutate our variable mapping
        return Locals(self.vars.copy(), copy.copy(self.parent_scope))

    def keys(self) -> set[str]:
        parent_keys = self.parent_scope.keys() if self.parent_scope else set()
        return parent_keys | self.vars.keys()

    def items(self) -> Iterable[tuple[str, Variable]]:
        parent_items = (
            iter(self.parent_scope.items()) if self.parent_scope else iter(())
        )
        return itertools.chain(self.vars.items(), parent_items)


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


def qualified_name(ty: TypeDef | str, name: str) -> str:
    """Returns a qualified name for an instance function on a type."""
    ty_name = ty if isinstance(ty, str) else ty.name
    return f"{ty_name}.{name}"
