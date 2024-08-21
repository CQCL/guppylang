import ast
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from hugr import Wire

from guppylang.ast_util import AstNode
from guppylang.definition.common import CompiledDef, Definition
from guppylang.error import GuppyError
from guppylang.tys.subst import Inst, Subst
from guppylang.tys.ty import FunctionType, Type

if TYPE_CHECKING:
    from guppylang.checker.core import Context
    from guppylang.compiler.core import CompiledGlobals, DFContainer


@dataclass(frozen=True)
class ValueDef(Definition):
    """Abstract base class for definitions that represent values."""

    ty: Type

    description: str = field(default="value", init=False)


@dataclass(frozen=True)
class CompiledValueDef(ValueDef, CompiledDef):
    """Abstract base class for compiled definitions that represent values."""

    @abstractmethod
    def load(
        self, dfg: "DFContainer", globals: "CompiledGlobals", node: AstNode
    ) -> Wire:
        """Loads the defined value into a local Hugr dataflow graph."""


@dataclass(frozen=True)
class CallableDef(ValueDef):
    """Abstract base class for definitions that represent functions."""

    ty: FunctionType

    @abstractmethod
    def check_call(
        self, args: list[ast.expr], ty: Type, node: AstNode, ctx: "Context"
    ) -> tuple[ast.expr, Subst]:
        """Checks the return type of a function call against a given type."""

    @abstractmethod
    def synthesize_call(
        self, args: list[ast.expr], node: AstNode, ctx: "Context"
    ) -> tuple[ast.expr, Type]:
        """Synthesizes the return type of a function call."""

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        raise GuppyError("Guppy functions can only be called in a Guppy context")


class CompiledCallableDef(CallableDef, CompiledValueDef):
    """Abstract base class a global module-level function."""

    ty: FunctionType

    @abstractmethod
    def compile_call(
        self,
        args: list[Wire],
        type_args: Inst,
        dfg: "DFContainer",
        globals: "CompiledGlobals",
        node: AstNode,
    ) -> list[Wire]:
        """Compiles a call to the function."""

    @abstractmethod
    def load_with_args(
        self,
        type_args: Inst,
        dfg: "DFContainer",
        globals: "CompiledGlobals",
        node: AstNode,
    ) -> Wire:
        """Loads the function into a local Hugr dataflow graph.

        Requires an instantiation for all function parameters.
        """

    def load(
        self, dfg: "DFContainer", globals: "CompiledGlobals", node: AstNode
    ) -> Wire:
        """Loads the defined value into a local Hugr dataflow graph."""
        return self.load_with_args([], dfg, globals, node)
