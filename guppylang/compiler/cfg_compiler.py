import functools
from collections.abc import Sequence

from hugr import Wire, ops
from hugr import tys as ht
from hugr.cfg import Block, Cfg
from hugr.dfg import DP, _DfBase
from hugr.node_port import ToNode

from guppylang.checker.cfg_checker import CheckedBB, CheckedCFG, Row, Signature
from guppylang.checker.core import Place, Variable
from guppylang.compiler.core import (
    CompiledGlobals,
    DFContainer,
    is_return_var,
    return_var,
)
from guppylang.compiler.expr_compiler import ExprCompiler
from guppylang.compiler.stmt_compiler import StmtCompiler
from guppylang.tys.ty import SumType, row_to_type, type_to_row


def compile_cfg(
    cfg: CheckedCFG[Place],
    container: _DfBase[DP],
    inputs: Sequence[Wire],
    globals: CompiledGlobals,
) -> Cfg:
    """Compiles a CFG to Hugr."""
    insert_return_vars(cfg)

    builder = container.add_cfg(*inputs)

    blocks: dict[CheckedBB[Place], ToNode] = {}
    for bb in cfg.bbs:
        blocks[bb] = compile_bb(bb, builder, bb == cfg.entry_bb, globals)
    for bb in cfg.bbs:
        for i, succ in enumerate(bb.successors):
            builder.branch(blocks[bb][i], blocks[succ])

    return builder


def compile_bb(
    bb: CheckedBB[Place],
    builder: Cfg,
    is_entry: bool,
    globals: CompiledGlobals,
) -> ToNode:
    """Compiles a single basic block to Hugr, and returns the resulting block.

    If the basic block is the output block, returns `None`.
    """
    # The exit BB is completely empty
    if len(bb.successors) == 0:
        assert len(bb.statements) == 0
        return builder.exit

    # Otherwise, we use a regular `Block` node
    block: Block
    inputs: Sequence[Place]
    if is_entry:
        inputs = bb.sig.input_row
        block = builder.add_entry()
    else:
        inputs = sort_vars(bb.sig.input_row)
        block = builder.add_block(*(v.ty.to_hugr() for v in inputs))

    # Add input node and compile the statements
    dfg = DFContainer(block)
    for v, wire in zip(inputs, block.input_node[:], strict=True):
        dfg[v] = wire
    dfg = StmtCompiler(globals).compile_stmts(bb.statements, dfg)

    # If we branch, we also have to compile the branch predicate
    if len(bb.successors) > 1:
        assert bb.branch_pred is not None
        branch_port = ExprCompiler(globals).compile(bb.branch_pred, dfg)
    else:
        # Even if we don't branch, we still have to add a `Sum(())` predicates
        branch_port = dfg.builder.add_op(ops.Tag(0, ht.UnitSum(1)))

    # Finally, we have to add the block output.
    outputs: Sequence[Place]
    if len(bb.successors) == 1:
        # The easy case is if we don't branch: We just output all variables that are
        # specified by the signature
        [outputs] = bb.sig.output_rows
    else:
        # If we branch and the branches use the same places, then we can use a
        # regular output
        first, *rest = bb.sig.output_rows
        if all({p.id for p in first} == {p.id for p in r} for r in rest):
            outputs = first
        else:
            # Otherwise, we have to output a TupleSum: We put all non-linear variables
            # into the branch TupleSum and all linear variables in the normal output
            # (since they are shared between all successors). This is in line with the
            # ordering on variables which puts linear variables at the end. The only
            # exception are return vars which must be outputted in order.
            branch_port = choose_vars_for_tuple_sum(
                unit_sum=branch_port,
                output_vars=[
                    [
                        v
                        for v in sort_vars(row)
                        if not v.ty.linear or is_return_var(str(v))
                    ]
                    for row in bb.sig.output_rows
                ],
                dfg=dfg,
            )
            outputs = [v for v in first if v.ty.linear and not is_return_var(str(v))]

    block.set_block_outputs(branch_port, *(dfg[v] for v in sort_vars(outputs)))
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
    # Before patching, the exit BB shouldn't take any inputs
    assert len(cfg.exit_bb.sig.input_row) == 0
    cfg.exit_bb.sig = Signature(return_vars, cfg.exit_bb.sig.output_rows)
    # Also patch the predecessors
    for pred in cfg.exit_bb.predecessors:
        # The exit BB will be the only successor
        assert len(pred.sig.output_rows) == 1
        assert len(pred.sig.output_rows[0]) == 0
        pred.sig = Signature(pred.sig.input_row, [return_vars])


def choose_vars_for_tuple_sum(
    unit_sum: Wire, output_vars: list[Row[Place]], dfg: DFContainer
) -> Wire:
    """Selects an output based on a TupleSum.

    Given `unit_sum: Sum(*(), *(), ...)` and output variable rows `#s1, #s2, ...`,
    constructs a TupleSum value of type `Sum(#s1, #s2, ...)`.
    """
    assert all(not v.ty.linear for var_row in output_vars for v in var_row)
    tys = [[v.ty for v in var_row] for var_row in output_vars]
    sum_type = SumType([row_to_type(row) for row in tys]).to_hugr()
    assert isinstance(sum_type, ht.Sum)

    with dfg.builder.add_conditional(unit_sum) as conditional:
        for i, var_row in enumerate(output_vars):
            with conditional.add_case(i) as case:
                tag = case.add_op(ops.Tag(i, sum_type), *(dfg[v] for v in var_row))
                case.set_outputs(tag)
        return conditional


def compare_var(p1: Place, p2: Place) -> int:
    """Defines a `<` order on variables.

    We use this to determine in which order variables are outputted from basic blocks.
    We need to output linear variables at the end, so we do a lexicographic ordering of
    linearity and name. The only exception are return vars which must be outputted in
    order.
    """
    x, y = str(p1), str(p2)
    if is_return_var(x) and is_return_var(y):
        return -1 if x < y else 1
    return -1 if (p1.ty.linear, x) < (p2.ty.linear, y) else 1


def sort_vars(row: Row[Place]) -> list[Place]:
    """Sorts a row of variables.

    This determines the order in which they are outputted from a BB.
    """
    return sorted(row, key=functools.cmp_to_key(compare_var))
