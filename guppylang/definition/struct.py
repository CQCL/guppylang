import ast
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from guppylang.ast_util import AstNode
from guppylang.checker.core import Globals
from guppylang.definition.common import (
    CheckableDef,
    CompiledDef,
    ParsableDef,
)
from guppylang.definition.ty import TypeDef
from guppylang.tys.arg import Argument
from guppylang.tys.param import Parameter
from guppylang.tys.ty import Type


@dataclass(frozen=True)
class UncheckedStructField:
    """A single field on a struct whose type has not been checked yet."""

    name: str
    type_ast: ast.expr


@dataclass(frozen=True)
class StructField:
    """A single field on a struct."""

    name: str
    ty: Type


@dataclass(frozen=True)
class RawStructDef(TypeDef, ParsableDef):
    """A raw struct type definition that has not been parsed yet."""

    python_class: type

    def __getitem__(self, item: Any) -> "RawStructDef":
        """Dummy implementation to enable subscripting in the Python runtime.

        For example, if users write `MyStruct[int]` in a function signature, the
        interpreter will try to execute the expression which would fail if this function
        weren't implemented.
        """
        return self

    def parse(self, globals: Globals) -> "ParsedStructDef":
        """Parses the raw class object into an AST and checks that it is well-formed."""
        raise NotImplementedError

    def check_instantiate(
        self, args: Sequence[Argument], globals: "Globals", loc: AstNode | None = None
    ) -> Type:
        raise NotImplementedError


@dataclass(frozen=True)
class ParsedStructDef(TypeDef, CheckableDef):
    """A struct definition whose fields have not been checked yet."""

    defined_at: ast.ClassDef
    params: Sequence[Parameter]
    fields: Sequence[UncheckedStructField]

    def check(self, globals: Globals) -> "CheckedStructDef":
        """Checks that all struct fields have valid types."""
        raise NotImplementedError

    def check_instantiate(
        self, args: Sequence[Argument], globals: "Globals", loc: AstNode | None = None
    ) -> Type:
        """Checks if the struct can be instantiated with the given arguments."""
        raise NotImplementedError


@dataclass(frozen=True)
class CheckedStructDef(TypeDef, CompiledDef):
    """A struct definition that has been fully checked."""

    defined_at: ast.ClassDef
    params: Sequence[Parameter]
    fields: Sequence[StructField]

    def check_instantiate(
        self, args: Sequence[Argument], globals: "Globals", loc: AstNode | None = None
    ) -> Type:
        """Checks if the struct can be instantiated with the given arguments."""
        raise NotImplementedError
