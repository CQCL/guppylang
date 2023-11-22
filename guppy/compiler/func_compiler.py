from dataclasses import dataclass

from guppy.ast_util import AstNode
from guppy.checker.func_checker import CheckedFunction, DefinedFunction
from guppy.compiler.core import (
    CompiledFunction,
    CompiledGlobals,
    DFContainer,
    PortVariable,
)
from guppy.hugr.hugr import Hugr, OutPortV, DFContainingVNode
from guppy.nodes import CheckedNestedFunctionDef


@dataclass
class CompiledFunctionDef(DefinedFunction, CompiledFunction):
    node: DFContainingVNode

    def load(
        self, dfg: DFContainer, graph: Hugr, globals: CompiledGlobals, node: AstNode
    ) -> OutPortV:
        raise NotImplementedError

    def compile_call(
        self,
        args: list[OutPortV],
        dfg: DFContainer,
        graph: Hugr,
        globals: CompiledGlobals,
        node: AstNode,
    ) -> list[OutPortV]:
        raise NotImplementedError


def compile_global_func_def(
    func: CheckedFunction,
    def_node: DFContainingVNode,
    graph: Hugr,
    globals: CompiledGlobals,
) -> CompiledFunctionDef:
    """Compiles a top-level function definition to Hugr."""
    raise NotImplementedError


def compile_local_func_def(
    func: CheckedNestedFunctionDef,
    dfg: DFContainer,
    graph: Hugr,
    globals: CompiledGlobals,
) -> PortVariable:
    """Compiles a local (nested) function definition to Hugr."""
    raise NotImplementedError
