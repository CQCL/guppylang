import ast
from dataclasses import dataclass, field

from hugr.serialization import ops

from guppylang.ast_util import AstNode
from guppylang.checker.core import Globals
from guppylang.compiler.core import CompiledGlobals, DFContainer
from guppylang.definition.common import CompilableDef, ParsableDef
from guppylang.definition.value import CompiledValueDef, ValueDef
from guppylang.hugr_builder.hugr import Hugr, Node, OutPortV, VNode
from guppylang.tys.parsing import type_from_ast


@dataclass(frozen=True)
class RawExternDef(ParsableDef):
    """A raw extern symbol definition provided by the user."""

    symbol: str
    constant: bool
    type_ast: ast.expr

    description: str = field(default="extern", init=False)

    def parse(self, globals: Globals) -> "ExternDef":
        """Parses and checks the user-provided signature of the function."""
        return ExternDef(
            self.id,
            self.name,
            self.defined_at,
            type_from_ast(self.type_ast, globals, None),
            self.symbol,
            self.constant,
            self.type_ast,
        )


@dataclass(frozen=True)
class ExternDef(RawExternDef, ValueDef, CompilableDef):
    """An extern symbol definition."""

    def compile_outer(self, graph: Hugr, parent: Node) -> "CompiledExternDef":
        """Adds a Hugr constant node for the extern definition to the provided graph."""
        custom_const = {
            "symbol": self.symbol,
            "typ": self.ty.to_hugr(),
            "constant": self.constant,
        }
        value = ops.ExtensionValue(
            extensions=["prelude"],
            typ=self.ty.to_hugr(),
            value=ops.CustomConst(c="ConstExternalSymbol", v=custom_const),
        )
        const_node = graph.add_constant(ops.Value(value), self.ty, parent)
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

    const_node: VNode

    def load(
        self, dfg: DFContainer, graph: Hugr, globals: CompiledGlobals, node: AstNode
    ) -> OutPortV:
        """Loads the extern value into a local Hugr dataflow graph."""
        return graph.add_load_constant(self.const_node.out_port(0)).out_port(0)
