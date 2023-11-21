import functools
from typing import Sequence

from guppy.checker.cfg_checker import CheckedBB, VarRow, CheckedCFG, Signature
from guppy.checker.core import Variable
from guppy.compiler.core import CompiledGlobals, is_return_var, DFContainer, return_var, \
    PortVariable
from guppy.compiler.expr_compiler import ExprCompiler
from guppy.compiler.stmt_compiler import StmtCompiler
from guppy.guppy_types import TupleType, SumType, type_to_row
from guppy.hugr.hugr import Hugr, Node, CFNode, OutPortV


def compile_cfg(cfg: CheckedCFG, graph: Hugr, parent: Node, globals: CompiledGlobals) -> None:
    """Compiles a CFG to Hugr."""
    insert_return_vars(cfg)

    blocks: dict[CheckedBB, CFNode] = {}
    for bb in cfg.bbs:
        blocks[bb] = compile_bb(bb, graph, parent, globals)
    for bb in cfg.bbs:
        for succ in bb.successors:
            graph.add_edge(blocks[bb].add_out_port(), blocks[succ].in_port(None))


def compile_bb(bb: CheckedBB, graph: Hugr, parent: Node, globals: CompiledGlobals) -> CFNode:
    """Compiles a single basic block to Hugr."""
    inputs = sort_vars(bb.sig.input_row)

    # The exit BB is completely empty
    if len(bb.successors) == 0:
        assert len(bb.statements) == 0
        return graph.add_exit([v.ty for v in inputs], parent)

    # Otherwise, we use a regular `Block` node
    block = graph.add_block(parent)

    # Add input node and compile the statements
    inp = graph.add_input(output_tys=[v.ty for v in inputs], parent=block)
    dfg = DFContainer(
        block,
        {
            v.name: PortVariable(v.name, inp.out_port(i), v.defined_at, None)
            for (i, v) in enumerate(inputs)
        },
    )
    dfg = StmtCompiler(graph, globals).compile_stmts(bb.statements, bb, dfg)

    # If we branch, we also have to compile the branch predicate
    if len(bb.successors) > 1:
        assert bb.branch_pred is not None
        branch_port = ExprCompiler(graph, globals).compile(bb.branch_pred, dfg)
    else:
        # Even if we don't branch, we still have to add a `Sum(())` predicates
        unit = graph.add_make_tuple([], parent=block).out_port(0)
        branch_port = graph.add_tag(
            variants=[TupleType([])], tag=0, inp=unit, parent=block
        ).out_port(0)

    # Finally, we have to add the block output.
    outputs: Sequence[Variable]
    if len(bb.successors) == 1:
        # The easy case is if we don't branch: We just output all variables that are
        # specified by the signature
        [outputs] = bb.sig.output_rows
    else:
        # If we branch and the branches use the same variables, then we can use a
        # regular output
        first, *rest = bb.sig.output_rows
        if all({v.name for v in first} == {v.name for v in r} for r in rest):
            outputs = first
        else:
            # Otherwise, we have to output a Sum-type predicate: We put all non-linear
            # variables into the branch predicate and all linear variables in the normal
            # output (since they are shared between all successors). This is in line
            # with the ordering on variables which puts linear variables at the end.
            # The only exception are return vars which must be outputted in order.
            branch_port = choose_vars_for_pred(
                graph=graph,
                pred=branch_port,
                output_vars=[
                    [v for v in row if not v.ty.linear or is_return_var(v.name)]
                    for row in bb.sig.output_rows
                ],
                dfg=dfg,
            )
            outputs = [v for v in first if v.ty.linear and not is_return_var(v.name)]

    graph.add_output(
        inputs=[branch_port] + [dfg[v.name].port for v in sort_vars(outputs)],
        parent=block,
    )
    return block


def insert_return_vars(cfg: CheckedCFG) -> None:
    """Patches a CFG by annotating dummy return variables in the BB signatures.

    The statement compiler turns `return` statements into assignments of dummy variables
    `%ret0`, `%ret1`, etc. We update the exit BB signature to make sure they are
    correctly outputted.
    """
    return_vars = [Variable(return_var(i), ty, None, None) for i, ty in enumerate(type_to_row(cfg.output_ty))]
    # Before patching, the exit BB shouldn't take any inputs
    assert len(cfg.exit_bb.sig.input_row) == 0
    cfg.exit_bb.sig = Signature(return_vars, cfg.exit_bb.sig.output_rows)
    # Also patch the predecessors
    for pred in cfg.exit_bb.predecessors:
        # The exit BB will be the only successor
        assert len(pred.sig.output_rows) == 1 and len(pred.sig.output_rows[0]) == 0
        pred.sig = Signature(pred.sig.input_row, [return_vars])


def choose_vars_for_pred(
    graph: Hugr, pred: OutPortV, output_vars: list[VarRow], dfg: DFContainer
) -> OutPortV:
    """Selects an output based on a predicate.

    Given `pred: Sum((), (), ...)` and output variable sets `#s1, #s2, ...`, constructs
    a predicate value of type `Sum(Tuple(#s1), Tuple(#s2), ...)`.
    """
    assert isinstance(pred.ty, SumType)
    assert len(pred.ty.element_types) == len(output_vars)
    tuples = [
        graph.add_make_tuple(
            inputs=[dfg[v.name].port for v in sort_vars(vs) if v.name in dfg], parent=dfg.node
        ).out_port(0)
        for vs in output_vars
    ]
    tys = [t.ty for t in tuples]
    conditional = graph.add_conditional(
        cond_input=pred, inputs=tuples, parent=dfg.node
    )
    for i, ty in enumerate(tys):
        case = graph.add_case(conditional)
        inp = graph.add_input(output_tys=tys, parent=case).out_port(i)
        tag = graph.add_tag(variants=tys, tag=i, inp=inp, parent=case).out_port(0)
        graph.add_output(inputs=[tag], parent=case)
    return conditional.add_out_port(SumType(tys))


def compare_var(x: Variable, y: Variable) -> int:
    """Defines a `<` order on variables.

    We use this to determine in which order variables are outputted from basic blocks.
    We need to output linear variables at the end, so we do a lexicographic ordering of
    linearity and name. The only exception are return vars which must be outputted in
    order.
    """
    if is_return_var(x.name) and is_return_var(y.name):
        return -1 if x.name < y.name else 1
    return -1 if (x.ty.linear, x.name) < (y.ty.linear, y.name) else 1


def sort_vars(row: VarRow) -> list[Variable]:
    """Sorts a row of variables.

    This determines the order in which they are outputted from a BB.
    """
    return sorted(row, key=functools.cmp_to_key(compare_var))

