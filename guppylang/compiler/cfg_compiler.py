import functools
from typing import TYPE_CHECKING

from guppylang.checker.cfg_checker import CheckedBB, CheckedCFG, Row, Signature
from guppylang.checker.core import Place, Variable
from guppylang.compiler.core import CompiledGlobals, DFContainer, return_var
from guppylang.compiler.expr_compiler import ExprCompiler
from guppylang.compiler.stmt_compiler import StmtCompiler
from guppylang.hugr_builder.hugr import CFNode, Hugr, Node, OutPortV
from guppylang.tys.builtin import is_bool_type
from guppylang.tys.ty import SumType, row_to_type, type_to_row

if TYPE_CHECKING:
    from collections.abc import Sequence


def compile_cfg(
    cfg: CheckedCFG[Place], graph: Hugr, parent: Node, globals: CompiledGlobals
) -> None:
    """Compiles a CFG to Hugr."""
    insert_return_vars(cfg)

    blocks: dict[CheckedBB[Place], CFNode] = {}
    for bb in cfg.bbs:
        blocks[bb] = compile_bb(bb, graph, parent, bb == cfg.entry_bb, globals)
    for bb in cfg.bbs:
        for succ in bb.successors:
            graph.add_edge(blocks[bb].add_out_port(), blocks[succ].in_port(None))


def compile_bb(
    bb: CheckedBB[Place],
    graph: Hugr,
    parent: Node,
    is_entry: bool,
    globals: CompiledGlobals,
) -> CFNode:
    """Compiles a single basic block to Hugr."""
    inputs = bb.sig.input_row if is_entry or bb.is_exit else sort_vars(bb.sig.input_row)

    # The exit BB is completely empty
    if len(bb.successors) == 0:
        assert len(bb.statements) == 0
        return graph.add_exit([v.ty for v in inputs], parent)

    # Otherwise, we use a regular `Block` node
    block = graph.add_block(parent)

    # Add input node and compile the statements
    inp = graph.add_input(output_tys=[v.ty for v in inputs], parent=block)
    dfg = DFContainer(graph, block)
    for i, v in enumerate(inputs):
        dfg[v] = inp.out_port(i)
    dfg = StmtCompiler(graph, globals).compile_stmts(bb.statements, dfg)

    # If we branch, we also have to compile the branch predicate
    if len(bb.successors) > 1:
        assert bb.branch_pred is not None
        branch_port = ExprCompiler(graph, globals).compile(bb.branch_pred, dfg)
    else:
        # Even if we don't branch, we still have to add a `Sum(())` predicates
        branch_port = graph.add_tag(
            variants=[[]], tag=0, inputs=[], parent=block
        ).out_port(0)

    # Finally, we have to add the block output.
    outputs: Sequence[Place]
    if len(bb.successors) == 1:
        # The easy case is if we don't branch: We just output all variables that are
        # specified by the signature
        [outputs] = bb.sig.output_rows
    else:
        # CFG building ensures that branching BBs don't branch to the exit (exit jumps
        # must always be unconditional)
        assert not any(succ.is_exit for succ in bb.successors)

        # If we branch and the branches use the same places, then we can use a
        # regular output
        first, *rest = bb.sig.output_rows
        if all({p.id for p in first} == {p.id for p in r} for r in rest):
            outputs = first
        else:
            # Otherwise, we have to output a TupleSum: We put all non-linear variables
            # into the branch TupleSum and all linear variables in the normal output
            # (since they are shared between all successors). This is in line with the
            # ordering on variables which puts linear variables at the end.
            # We don't need to worry about the order of return vars since this isn't
            # a branch to an exit (see assert above).
            branch_port = choose_vars_for_tuple_sum(
                graph=graph,
                unit_sum=branch_port,
                output_vars=[
                    [v for v in sort_vars(row) if not v.ty.linear]
                    for row in bb.sig.output_rows
                ],
                dfg=dfg,
            )
            outputs = [v for v in first if v.ty.linear]

    # If this is *not* a jump to the exit BB, we need to sort the outputs to make the
    # signature consistent with what the next BB expects
    if not any(succ.is_exit for succ in bb.successors):
        outputs = sort_vars(outputs)
    else:
        # Exit variables are not allowed to be sorted since their order corresponds to
        # the function outputs
        assert len(bb.successors) == 1, "Exit jumps are always unconditional"

    graph.add_output(inputs=[branch_port] + [dfg[v] for v in outputs], parent=block)
    return block


def insert_return_vars(cfg: CheckedCFG[Place]) -> None:
    """Patches a CFG by annotating dummy return variables in the BB signatures.

    The statement compiler turns `return` statements into assignments of dummy variables
    `%ret0`, `%ret1`, etc. We update the exit BB signature to make sure they are
    correctly outputted.
    """
    return_vars = [
        Variable(return_var(i), ty, None)
        for i, ty in enumerate(type_to_row(cfg.output_ty))
    ]
    # Prepend return variables to the exit signature
    cfg.exit_bb.sig = Signature(
        [*return_vars, *cfg.exit_bb.sig.input_row], cfg.exit_bb.sig.output_rows
    )
    # Also patch the predecessors
    for pred in cfg.exit_bb.predecessors:
        # The exit BB will be the only successor
        assert len(pred.sig.output_rows) == 1
        [out_row] = pred.sig.output_rows
        pred.sig = Signature(pred.sig.input_row, [[*return_vars, *out_row]])


def choose_vars_for_tuple_sum(
    graph: Hugr, unit_sum: OutPortV, output_vars: list[Row[Place]], dfg: DFContainer
) -> OutPortV:
    """Selects an output based on a TupleSum.

    Given `unit_sum: Sum(*(), *(), ...)` and output variable rows `#s1, #s2, ...`,
    constructs a TupleSum value of type `Sum(#s1, #s2, ...)`.
    """
    assert isinstance(unit_sum.ty, SumType) or is_bool_type(unit_sum.ty)
    assert len(output_vars) == (
        len(unit_sum.ty.element_types) if isinstance(unit_sum.ty, SumType) else 2
    )
    assert all(not v.ty.linear for var_row in output_vars for v in var_row)
    conditional = graph.add_conditional(cond_input=unit_sum, inputs=[], parent=dfg.node)
    tys = [[v.ty for v in var_row] for var_row in output_vars]
    for i, var_row in enumerate(output_vars):
        case = graph.add_case(conditional)
        graph.add_input(output_tys=[], parent=case)
        inputs = [dfg[v] for v in var_row]
        tag = graph.add_tag(variants=tys, tag=i, inputs=inputs, parent=case).out_port(0)
        graph.add_output(inputs=[tag], parent=case)
    return conditional.add_out_port(SumType([row_to_type(row) for row in tys]))


def compare_var(p1: Place, p2: Place) -> int:
    """Defines a `<` order on variables.

    We use this to determine in which order variables are outputted from basic blocks.
    We need to output linear variables at the end, so we do a lexicographic ordering of
    linearity and name.
    """
    return -1 if (p1.ty.linear, str(p1)) < (p2.ty.linear, str(p2)) else 1


def sort_vars(row: Row[Place]) -> list[Place]:
    """Sorts a row of variables.

    This determines the order in which they are outputted from a BB.
    """
    return sorted(row, key=functools.cmp_to_key(compare_var))
