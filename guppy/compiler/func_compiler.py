from dataclasses import dataclass

from guppy.ast_util import AstNode
from guppy.checker.func_checker import CheckedFunction, DefinedFunction
from guppy.compiler.cfg_compiler import compile_cfg
from guppy.compiler.core import (
    CompiledFunction,
    CompiledGlobals,
    DFContainer,
    PortVariable,
)
from guppy.gtypes import type_to_row, FunctionType
from guppy.hugr.hugr import Hugr, OutPortV, DFContainingVNode
from guppy.nodes import CheckedNestedFunctionDef


@dataclass
class CompiledFunctionDef(DefinedFunction, CompiledFunction):
    node: DFContainingVNode

    def load(
        self, dfg: DFContainer, graph: Hugr, globals: CompiledGlobals, node: AstNode
    ) -> OutPortV:
        return graph.add_load_constant(self.node.out_port(0), dfg.node).out_port(0)

    def compile_call(
        self,
        args: list[OutPortV],
        dfg: DFContainer,
        graph: Hugr,
        globals: CompiledGlobals,
        node: AstNode,
    ) -> list[OutPortV]:
        call = graph.add_call(self.node.out_port(0), args, dfg.node)
        return [call.out_port(i) for i in range(len(type_to_row(self.ty.returns)))]


def compile_global_func_def(
    func: CheckedFunction,
    def_node: DFContainingVNode,
    graph: Hugr,
    globals: CompiledGlobals,
) -> CompiledFunctionDef:
    """Compiles a top-level function definition to Hugr."""
    def_input = graph.add_input(parent=def_node)
    cfg_node = graph.add_cfg(
        def_node, inputs=[def_input.add_out_port(ty) for ty in func.ty.args]
    )
    compile_cfg(func.cfg, graph, cfg_node, globals)

    # Add output node for the cfg
    graph.add_output(
        inputs=[cfg_node.add_out_port(ty) for ty in type_to_row(func.cfg.output_ty)],
        parent=def_node,
    )

    return CompiledFunctionDef(func.name, func.ty, func.defined_at, None, def_node)


def compile_local_func_def(
    func: CheckedNestedFunctionDef,
    dfg: DFContainer,
    graph: Hugr,
    globals: CompiledGlobals,
) -> PortVariable:
    """Compiles a local (nested) function definition to Hugr."""
    assert func.ty.arg_names is not None

    # Pick an order for the captured variables
    captured = list(func.captured.values())

    # Prepend captured variables to the function arguments
    closure_ty = FunctionType(
        [v.ty for v in captured] + list(func.ty.args),
        func.ty.returns,
        [v.name for v in captured] + list(func.ty.arg_names),
    )

    def_node = graph.add_def(closure_ty, dfg.node, func.name)
    def_input = graph.add_input(parent=def_node)
    input_ports = [def_input.add_out_port(ty) for ty in closure_ty.args]

    # If we have captured variables and the body contains a recursive occurrence of
    # the function itself, then we provide the partially applied function as a local
    # variable
    if len(captured) > 0 and func.name in func.cfg.live_before[func.cfg.entry_bb]:
        loaded = graph.add_load_constant(def_node.out_port(0), def_node).out_port(0)
        partial = graph.add_partial(
            loaded, [def_input.out_port(i) for i in range(len(captured))], def_node
        )
        input_ports.append(partial.out_port(0))
        func.cfg.input_tys.append(func.ty)
    else:
        # Otherwise, we treat the function like a normal global variable
        globals = globals | {
            func.name: CompiledFunctionDef(func.name, func.ty, func, None, def_node)
        }

    # Compile the CFG
    cfg_node = graph.add_cfg(def_node, inputs=input_ports)
    compile_cfg(func.cfg, graph, cfg_node, globals)

    # Add output node for the cfg
    graph.add_output(
        inputs=[cfg_node.add_out_port(ty) for ty in type_to_row(func.cfg.output_ty)],
        parent=def_node,
    )

    # Finally, load the function into the local data-flow graph
    loaded = graph.add_load_constant(def_node.out_port(0), dfg.node).out_port(0)
    if len(captured) > 0:
        loaded = graph.add_partial(
            loaded, [dfg[v.name].port for v in captured], dfg.node
        ).out_port(0)

    return PortVariable(func.name, loaded, func)
