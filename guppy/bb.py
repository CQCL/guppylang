import ast
from dataclasses import dataclass, field
from typing import Optional

from guppy.ast_util import Assign
from guppy.compiler_base import Signature, DFContainer, Variable, VarMap
from guppy.error import assert_bool_type
from guppy.expression import ExpressionCompiler
from guppy.guppy_types import GuppyType, SumType, TupleType
from guppy.hugr.hugr import CFNode, Node, Hugr, OutPortV
from guppy.statement import StatementCompiler


@dataclass
class VarAnalysis:
    # Variables that are assigned in the BB
    assigned: dict[str, Assign] = field(default_factory=dict)

    # The (external) variables used in the BB, i.e. usages of variables that are
    # assigned in the BB are not included here.
    used: dict[str, ast.Name] = field(default_factory=dict)

    # Variables that are live before the execution of the BB. We store the BB in which
    # the use occurs as evidence of liveness
    live_before: dict[str, "BB"] = field(default_factory=dict)

    # Variables that are definitely assigned before the execution of the BB
    assigned_before: set[str] = field(default_factory=set)

    # Variables that are possibly assigned before the execution of the BB, i.e. the
    # variable is defined on some paths, but not all of them.
    maybe_assigned_before: set[str] = field(default_factory=set)


@dataclass(eq=False)  # Disable equality to recover hash from `object`
class BB:
    """A basic block in a control flow graph."""

    idx: int

    # AST statements contained in this BB
    statements: list[ast.stmt] = field(default_factory=list)

    # Predecessor and successor BBs
    predecessors: list["BB"] = field(default_factory=list)
    successors: list["BB"] = field(default_factory=list)

    # If the BB has multiple successors, we need a predicate to decide to which one to
    # jump to
    branch_pred: Optional[ast.expr] = None

    # Program analysis data
    vars: VarAnalysis = field(default_factory=VarAnalysis)

    def compile(
        self, graph: Hugr, sig: Signature, return_tys: list[GuppyType], parent: Node, global_variables: VarMap
    ) -> "CompiledBB":
        """Compiles this basic block.

        Note that liveness and definite assignment analysis must be performed before
        this compile function is called.
        """
        # The exit BB is completely empty
        if len(self.successors) == 0:
            block = graph.add_exit(return_tys, parent)
            return CompiledBB(block, self, sig, [])

        block = graph.add_block(parent)
        inp = graph.add_input(output_tys=[v.ty for v in sig], parent=block)
        dfg = DFContainer(
            block,
            {
                v.name: Variable(v.name, inp.out_port(i), v.defined_at)
                for (i, v) in enumerate(sig)
            },
        )

        stmt_compiler = StatementCompiler(graph, global_variables)
        dfg = stmt_compiler.compile_stmts(self.statements, dfg, return_tys)

        # The easy case is if we don't branch. We just output the variables that are
        # live in the successor
        if len(self.successors) == 1:
            outputs = [dfg[x].port for x in self.successors[0].vars.live_before if
                       x in dfg]
            # Even if wo don't branch, we still have to add a unit `Sum(())` predicate
            unit = graph.add_make_tuple([], parent=block).out_port(0)
            branch_port = graph.add_tag(
                variants=[TupleType([])], tag=0, inp=unit, parent=block
            ).out_port(0)

        # If we branch, we have to compile the branch predicate
        else:
            assert self.branch_pred is not None
            expr_compiler = ExpressionCompiler(graph, global_variables)
            branch_port = expr_compiler.compile(self.branch_pred, dfg)
            assert_bool_type(branch_port.ty, self.branch_pred)
            # If the branches use different variables, we have to use the predicate
            # output feature.
            if any(
                s.vars.live_before.keys() != self.successors[0].vars.live_before.keys()
                for s in self.successors[1:]
            ):
                branch_port = _make_predicate_output(
                    graph=graph,
                    pred=branch_port,
                    output_vars=[
                        set(succ.vars.live_before.keys() & dfg.variables.keys())
                        for succ in self.successors
                    ],
                    dfg=dfg,
                )
                outputs = []
            else:
                outputs = [dfg[x].port for x in self.successors[0].vars.live_before if
                           x in dfg]

        graph.add_output(inputs=[branch_port] + outputs, parent=block)

        return CompiledBB(
            block,
            self,
            sig,
            [[dfg[x] for x in succ.vars.live_before if x in dfg] for succ in
             self.successors],
        )


@dataclass
class CompiledBB:
    node: CFNode
    bb: BB
    # TODO: Refactor: Turn `Signature` into dataclass with `input` and `outputs`
    input_sig: Signature
    output_sigs: list[Signature]  # One for each successor


def _make_predicate_output(
    graph: Hugr, pred: OutPortV, output_vars: list[set[str]], dfg: DFContainer
) -> OutPortV:
    """Selects an output based on a predicate.

    Given `pred: Sum((), (), ...)` and output variable sets `#s1, #s2, ...`,
    constructs a predicate value of type `Sum(Tuple(#s1), Tuple(#s2), ...)`.
    """
    assert isinstance(pred.ty, SumType) and len(pred.ty.element_types) == len(
        output_vars
    )
    tuples = [
        graph.add_make_tuple(
            inputs=[dfg[x].port for x in sorted(vs) if x in dfg], parent=dfg.node
        ).out_port(0)
        for vs in output_vars
    ]
    tys = [t.ty for t in tuples]
    conditional = graph.add_conditional(cond_input=pred, inputs=tuples, parent=dfg.node)
    for i, ty in enumerate(tys):
        case = graph.add_case(conditional)
        inp = graph.add_input(output_tys=tys, parent=case).out_port(i)
        tag = graph.add_tag(variants=tys, tag=i, inp=inp, parent=case).out_port(0)
        graph.add_output(inputs=[tag], parent=case)
    return conditional.add_out_port(SumType([t.ty for t in tuples]))
