import ast
import collections
import itertools
from typing import Optional, NamedTuple, Iterator, Union

from guppy.cfg.analysis import (
    LivenessDomain,
    LivenessAnalysis,
    AssignmentAnalysis,
    DefAssignmentDomain,
    MaybeAssignmentDomain,
    Result,
)
from guppy.cfg.bb import (
    BB,
    VarRow,
    Signature,
    CompiledBB,
    NestedFunctionDef,
    BBStatement,
)
from guppy.compiler_base import VarMap, DFContainer, Variable, Globals
from guppy.error import InternalGuppyError, GuppyError, GuppyTypeError
from guppy.ast_util import AstVisitor, line_col, set_location_from
from guppy.expression import ExpressionCompiler
from guppy.guppy_types import GuppyType, TupleType, SumType
from guppy.hugr.hugr import Node, Hugr, OutPortV
from guppy.statement import StatementCompiler


class CFG:
    """A control-flow graph of basic blocks."""

    bbs: list[BB]
    entry_bb: BB
    exit_bb: BB

    live_before: Result[LivenessDomain]
    ass_before: Result[DefAssignmentDomain]
    maybe_ass_before: Result[MaybeAssignmentDomain]

    def __init__(self) -> None:
        self.bbs = []
        self.entry_bb = self.new_bb()
        self.exit_bb = self.new_bb()
        self.live_before = {}
        self.ass_before = {}
        self.maybe_ass_before = {}

    def new_bb(self, *preds: BB, statements: Optional[list[BBStatement]] = None) -> BB:
        """Adds a new basic block to the CFG."""
        bb = BB(
            len(self.bbs), self, predecessors=list(preds), statements=statements or []
        )
        self.bbs.append(bb)
        for p in preds:
            p.successors.append(bb)
        return bb

    def link(self, src_bb: BB, tgt_bb: BB) -> None:
        """Adds a control-flow edge between two basic blocks."""
        src_bb.successors.append(tgt_bb)
        tgt_bb.predecessors.append(src_bb)

    def analyze(
        self, num_returns: int, def_ass_before: set[str], maybe_ass_before: set[str]
    ) -> None:
        for bb in self.bbs:
            bb.compute_variable_stats(num_returns)
        self.live_before = LivenessAnalysis().run(self.bbs)
        self.ass_before, self.maybe_ass_before = AssignmentAnalysis(
            self.bbs, def_ass_before, maybe_ass_before
        ).run_unpacked(self.bbs)

    def compile(
        self,
        graph: Hugr,
        input_row: VarRow,
        return_tys: list[GuppyType],
        parent: Node,
        globals: Globals,
    ) -> None:
        """Compiles the CFG."""

        # First, we need to run program analysis
        ass_before = {v.name for v in input_row}
        self.analyze(len(return_tys), ass_before, ass_before)

        # We start by compiling the entry BB
        entry_compiled = self._compile_bb(
            self.entry_bb, input_row, return_tys, graph, parent, globals
        )
        compiled = {self.entry_bb: entry_compiled}

        # Visit all control-flow edges in BFS order. We can't just do a normal loop over
        # all BBs since the input types for a BB are computed by compiling a predecessor
        queue = collections.deque(
            (entry_compiled, i, succ) for i, succ in enumerate(self.entry_bb.successors)
        )
        while len(queue) > 0:
            pred, num_output, bb = queue.popleft()
            out_row = pred.sig.output_rows[num_output]

            if bb in compiled:
                # If the BB was already compiled, we just have to check that the
                # signatures match.
                self._check_rows_match(out_row, compiled[bb].sig.input_row, bb)
            else:
                # Otherwise, compile the BB and enqueue its successors
                compiled_bb = self._compile_bb(
                    bb, out_row, return_tys, graph, parent, globals
                )
                queue += [
                    (compiled_bb, i, succ) for i, succ in enumerate(bb.successors)
                ]
                compiled[bb] = compiled_bb

            graph.add_edge(
                pred.node.out_port(num_output), compiled[bb].node.in_port(None)
            )

    def _compile_bb(
        self,
        bb: BB,
        input_row: VarRow,
        return_tys: list[GuppyType],
        graph: Hugr,
        parent: Node,
        globals: Globals,
    ) -> CompiledBB:
        """Compiles a single basic block."""

        # The exit BB is completely empty
        if len(bb.successors) == 0:
            block = graph.add_exit(return_tys, parent)
            return CompiledBB(block, bb, Signature(input_row, []))

        # For the entry BB we have to separately check that all used variables are
        # defined. For all other BBs, this will be checked when compiling a predecessor.
        if len(bb.predecessors) == 0:
            for x, use in bb.vars.used.items():
                if x not in self.ass_before[bb] and x not in globals.values:
                    raise GuppyError(f"Variable `{x}` is not defined", use)

        # Compile the basic block
        block = graph.add_block(parent, num_successors=len(bb.successors))
        inp = graph.add_input(output_tys=[v.ty for v in input_row], parent=block)
        dfg = DFContainer(
            block,
            {
                v.name: Variable(v.name, inp.out_port(i), v.defined_at)
                for (i, v) in enumerate(input_row)
            },
        )
        stmt_compiler = StatementCompiler(graph, globals)
        dfg = stmt_compiler.compile_stmts(bb.statements, bb, dfg, return_tys)

        # If we branch, we also have to compile the branch predicate
        if len(bb.successors) > 1:
            assert bb.branch_pred is not None
            expr_compiler = ExpressionCompiler(graph, globals)
            port = expr_compiler.compile(bb.branch_pred, dfg)
            func = globals.get_instance_func(port.ty, "__bool__")
            if func is None:
                raise GuppyTypeError(
                    f"Expression of type `{port.ty}` cannot be interpreted as a `bool`",
                    bb.branch_pred
                )
            [branch_port] = func.compile_call(
                [port], dfg.node, graph, globals, bb.branch_pred
            )

        for succ in bb.successors:
            for x, use_bb in self.live_before[succ].items():
                # Check that the variable requested by the successor are defined
                if x not in dfg and x not in globals.values:
                    # If the variable is defined on *some* paths, we can give a more
                    # informative error message
                    if x in self.maybe_ass_before[use_bb]:
                        # TODO: This should be "Variable x is not defined when coming
                        #  from {bb}". But for this we need a way to associate BBs with
                        #  source locations.
                        raise GuppyError(
                            f"Variable `{x}` is not defined on all control-flow paths.",
                            use_bb.vars.used[x],
                        )
                    raise GuppyError(
                        f"Variable `{x}` is not defined", use_bb.vars.used[x]
                    )

                # We have to check that used linear variables are not being outputted
                if x in dfg:
                    var = dfg[x]
                    if var.ty.linear and var.used:
                        raise GuppyError(
                            f"Variable `{x}` with linear type `{var.ty}` was "
                            "already used (at {0})",
                            self.live_before[succ][x].vars.used[x],
                            [var.used],
                        )

            # On the other hand, unused linear variables *must* be outputted
            for x, var in dfg.variables.items():
                if var.ty.linear and not var.used and x not in self.live_before[succ]:
                    # TODO: This should be "Variable x with linear type ty is not
                    #  used in {bb}". But for this we need a way to associate BBs with
                    #  source locations.
                    raise GuppyError(
                        f"Variable `{x}` with linear type `{var.ty}` is "
                        "not used on all control-flow paths",
                        var.defined_at,
                    )

        # Finally, we have to add the block output. The easy case is if we don't branch:
        # We just output the variables that are live in the successor
        output_vars = sorted(
            dfg[x] for x in self.live_before[bb.successors[0]] if x in dfg
        )
        if len(bb.successors) == 1:
            # Even if we don't branch, we still have to add a `Sum(())` predicate
            unit = graph.add_make_tuple([], parent=block).out_port(0)
            branch_port = graph.add_tag(
                variants=[TupleType([])], tag=0, inp=unit, parent=block
            ).out_port(0)
        else:
            # If we branch and the branches use different variables, we have to output a
            # Sum-type predicate
            first, *rest = bb.successors
            if any(
                self.live_before[r].keys() != self.live_before[first].keys()
                for r in rest
            ):
                # We put all non-linear variables into the branch predicate and all
                # linear variables in the normal output (since they are shared between
                # all successors). This is in line with the definition of `<` on
                # variables which puts linear variables at the end.
                branch_port = self._choose_vars_for_pred(
                    graph=graph,
                    pred=branch_port,
                    output_vars=[
                        sorted(
                            x
                            for x in self.live_before[succ]
                            if x in dfg and not dfg[x].ty.linear
                        )
                        for succ in bb.successors
                    ],
                    dfg=dfg,
                )
                output_vars = sorted(
                    dfg[x]
                    # We can look at `successors[0]` here since all successors must have
                    # the same `live_before` linear variables
                    for x in self.live_before[bb.successors[0]]
                    if x in dfg and dfg[x].ty.linear
                )

        graph.add_output(
            inputs=[branch_port] + [v.port for v in output_vars], parent=block
        )
        output_rows = [
            sorted([dfg[x] for x in self.live_before[succ] if x in dfg])
            for succ in bb.successors
        ]

        return CompiledBB(block, bb, Signature(input_row, output_rows))

    def _check_rows_match(self, row1: VarRow, row2: VarRow, bb: BB) -> None:
        """Checks that the types of two rows match up.

        Otherwise, an error is thrown, alerting the user that a variable has different
        types on different control-flow paths.
        """
        assert len(row1) == len(row2)
        for v1, v2 in zip(row1, row2):
            assert v1.name == v2.name
            if v1.ty != v2.ty:
                # In the error message, we want to mention the variable that was first
                # defined at the start.
                if v1.defined_at and v2.defined_at and line_col(v2.defined_at) < line_col(v1.defined_at):
                    v1, v2 = v2, v1
                # We shouldn't mention temporary variables (starting with `%`)
                # in error messages:
                ident = (
                    "Expression" if v1.name.startswith("%") else f"Variable `{v1.name}`"
                )
                raise GuppyError(
                    f"{ident} can refer to different types: "
                    f"`{v1.ty}` (at {{}}) vs `{v2.ty}` (at {{}})",
                    self.live_before[bb][v1.name].vars.used[v1.name],
                    [v1.defined_at, v2.defined_at],
                )

    @staticmethod
    def _choose_vars_for_pred(
        graph: Hugr, pred: OutPortV, output_vars: list[list[str]], dfg: DFContainer
    ) -> OutPortV:
        """Selects an output based on a predicate.

        Given `pred: Sum((), (), ...)` and output variable sets `#s1, #s2, ...`,
        constructs a predicate value of type `Sum(Tuple(#s1), Tuple(#s2), ...)`.
        """
        assert isinstance(pred.ty, SumType)
        assert len(pred.ty.element_types) == len(output_vars)
        tuples = [
            graph.add_make_tuple(
                inputs=[dfg[x].port for x in sorted(vs) if x in dfg], parent=dfg.node
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
