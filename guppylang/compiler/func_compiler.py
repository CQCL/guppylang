from dataclasses import dataclass

from guppylang.ast_util import AstNode
from guppylang.checker.func_checker import CheckedFunction, DefinedFunction
from guppylang.compiler.cfg_compiler import compile_cfg
from guppylang.compiler.core import (
    CompiledFunction,
    CompiledGlobals,
    DFContainer,
    PortVariable,
)
from guppylang.gtypes import FunctionType, Inst, type_to_row
from guppylang.hugr.hugr import DFContainingVNode, Hugr, OutPortV
from guppylang.nodes import CheckedNestedFunctionDef


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
        type_args: Inst,
        dfg: DFContainer,
        graph: Hugr,
        globals: CompiledGlobals,
        node: AstNode,
    ) -> list[OutPortV]:
        # TODO: Hugr should probably allow us to pass type args to `Call`, so we can
        #   avoid loading the function to manually add a `TypeApply`
        if type_args:
            func = graph.add_load_constant(self.node.out_port(0), dfg.node)
            func = graph.add_type_apply(func.out_port(0), type_args, dfg.node)
            call = graph.add_indirect_call(func.out_port(0), args, dfg.node)
        else:
            call = graph.add_call(self.node.out_port(0), args, dfg.node)
        return [call.out_port(i) for i in range(len(type_to_row(self.ty.returns)))]


def compile_global_func_def(
    func: CheckedFunction,
    def_node: DFContainingVNode,
    graph: Hugr,
    globals: CompiledGlobals,
) -> CompiledFunctionDef:
    """Compiles a top-level function definition to Hugr."""
    _, ports = graph.add_input_with_ports(list(func.ty.args), def_node)
    cfg_node = graph.add_cfg(def_node, ports)
    compile_cfg(func.cfg, graph, cfg_node, globals)

    # Add output node for the cfg
    graph.add_output(
        inputs=[cfg_node.add_out_port(ty) for ty in type_to_row(func.cfg.output_ty)],
        parent=def_node,
    )

    return CompiledFunctionDef(
        func.name, func.ty, func.defined_at, None, func.module, def_node
    )


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
    def_input, input_ports = graph.add_input_with_ports(list(closure_ty.args), def_node)

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
            func.name: CompiledFunctionDef(
                func.name, func.ty, func, None, None, def_node
            )
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
