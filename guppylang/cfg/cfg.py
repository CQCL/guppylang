from typing import Generic, TypeVar

from guppylang.cfg.analysis import (
    AssignmentAnalysis,
    DefAssignmentDomain,
    LivenessAnalysis,
    LivenessDomain,
    MaybeAssignmentDomain,
    Result,
)
from guppylang.cfg.bb import BB, BBStatement

T = TypeVar("T", bound=BB)


class BaseCFG(Generic[T]):
    """Abstract base class for control-flow graphs."""

    bbs: list[T]
    entry_bb: T
    exit_bb: T

    live_before: Result[LivenessDomain]
    ass_before: Result[DefAssignmentDomain]
    maybe_ass_before: Result[MaybeAssignmentDomain]

    def __init__(
        self, bbs: list[T], entry_bb: T | None = None, exit_bb: T | None = None
    ):
        self.bbs = bbs
        if entry_bb:
            self.entry_bb = entry_bb
        if exit_bb:
            self.exit_bb = exit_bb
        self.live_before = {}
        self.ass_before = {}
        self.maybe_ass_before = {}

    def analyze(self, def_ass_before: set[str], maybe_ass_before: set[str]) -> None:
        for bb in self.bbs:
            bb.compute_variable_stats()
        self.live_before = LivenessAnalysis().run(self.bbs)
        self.ass_before, self.maybe_ass_before = AssignmentAnalysis(
            self.bbs, def_ass_before, maybe_ass_before
        ).run_unpacked(self.bbs)


class CFG(BaseCFG[BB]):
    """A control-flow graph of unchecked basic blocks."""

    def __init__(self) -> None:
        super().__init__([])
        self.entry_bb = self.new_bb()
        self.exit_bb = self.new_bb()

    def new_bb(self, *preds: BB, statements: list[BBStatement] | None = None) -> BB:
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
