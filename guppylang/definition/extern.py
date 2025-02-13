import ast
from dataclasses import dataclass, field

from hugr import Node, Wire, val
from hugr.build.dfg import DefinitionBuilder, OpVar

from guppylang.ast_util import AstNode
from guppylang.checker.core import Globals
from guppylang.compiler.core import CompilerContext, DFContainer
from guppylang.definition.common import CompilableDef, ParsableDef
from guppylang.definition.value import CompiledValueDef, ValueDef
from guppylang.span import SourceMap
from guppylang.tys.parsing import type_from_ast


@dataclass(frozen=True)
class RawExternDef(ParsableDef):
    """A raw extern symbol definition provided by the user."""

    symbol: str
    constant: bool
    type_ast: ast.expr

    description: str = field(default="extern", init=False)

    def parse(self, globals: Globals, sources: SourceMap) -> "ExternDef":
        """Parses and checks the user-provided signature of the function."""
        return ExternDef(
            self.id,
            self.name,
            self.defined_at,
            type_from_ast(self.type_ast, globals, {}),
            self.symbol,
            self.constant,
            self.type_ast,
        )


@dataclass(frozen=True)
class ExternDef(RawExternDef, ValueDef, CompilableDef):
    """An extern symbol definition."""

    def compile_outer(self, graph: DefinitionBuilder[OpVar]) -> "CompiledExternDef":
        """Adds a Hugr constant node for the extern definition to the provided graph."""
        # The `typ` field must be serialized at this point, to ensure that the
        # `Extension` is serializable.
        custom_const = {
            "symbol": self.symbol,
            "typ": self.ty.to_hugr()._to_serial_root(),
            "constant": self.constant,
        }
        value = val.Extension(
            name="ConstExternalSymbol",
            typ=self.ty.to_hugr(),
            val=custom_const,
            extensions=["prelude"],
        )
        const_node = graph.add_const(value)
        return CompiledExternDef(
            self.id,
            self.name,
            self.defined_at,
            self.ty,
            self.symbol,
            self.constant,
            self.type_ast,
            const_node,
        )


@dataclass(frozen=True)
class CompiledExternDef(ExternDef, CompiledValueDef):
    """An extern symbol definition that has been compiled to a Hugr constant."""

    const_node: Node

    def load(self, dfg: DFContainer, ctx: CompilerContext, node: AstNode) -> Wire:
        """Loads the extern value into a local Hugr dataflow graph."""
        return dfg.builder.load(self.const_node)
