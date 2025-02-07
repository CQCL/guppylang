import ast
from dataclasses import dataclass, field

from hugr import Node, Wire
from hugr import val as hv
from hugr.build.dfg import DefinitionBuilder, OpVar

from guppylang.ast_util import AstNode
from guppylang.checker.core import Globals
from guppylang.compiler.core import CompilerContext, DFContainer
from guppylang.definition.common import CompilableDef, ParsableDef
from guppylang.definition.value import CompiledValueDef, ValueDef
from guppylang.span import SourceMap
from guppylang.tys.parsing import type_from_ast


@dataclass(frozen=True)
class RawConstDef(ParsableDef):
    """A raw constant definition as provided by the user."""

    type_ast: ast.expr
    value: hv.Value

    description: str = field(default="constant", init=False)

    def parse(self, globals: Globals, sources: SourceMap) -> "ConstDef":
        """Parses and checks the user-provided signature of the function."""
        return ConstDef(
            self.id,
            self.name,
            self.defined_at,
            type_from_ast(self.type_ast, globals, {}),
            self.type_ast,
            self.value,
        )


@dataclass(frozen=True)
class ConstDef(RawConstDef, ValueDef, CompilableDef):
    """A constant with a checked type."""

    def compile_outer(self, graph: DefinitionBuilder[OpVar]) -> "CompiledConstDef":
        const_node = graph.add_const(self.value)
        return CompiledConstDef(
            self.id,
            self.name,
            self.defined_at,
            self.ty,
            self.type_ast,
            self.value,
            const_node,
        )


@dataclass(frozen=True)
class CompiledConstDef(ConstDef, CompiledValueDef):
    """A constant that has been compiled to a Hugr node."""

    const_node: Node

    def load(self, dfg: DFContainer, ctx: CompilerContext, node: AstNode) -> Wire:
        """Loads the extern value into a local Hugr dataflow graph."""
        return dfg.builder.load(self.const_node)
