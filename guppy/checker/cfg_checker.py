from dataclasses import dataclass
from typing import Sequence

from guppy.cfg.bb import BB
from guppy.cfg.cfg import CFG, BaseCFG
from guppy.checker.core import Globals

from guppy.checker.core import Variable
from guppy.gtypes import GuppyType


VarRow = Sequence[Variable]


@dataclass(frozen=True)
class Signature:
    """The signature of a basic block.

    Stores the input/output variables with their types.
    """

    input_row: VarRow
    output_rows: Sequence[VarRow]  # One for each successor

    @staticmethod
    def empty() -> "Signature":
        return Signature([], [])


@dataclass(eq=False)  # Disable equality to recover hash from `object`
class CheckedBB(BB):
    """Basic block annotated with an input and output type signature."""

    sig: Signature = Signature.empty()


class CheckedCFG(BaseCFG[CheckedBB]):
    input_tys: list[GuppyType]
    output_ty: GuppyType

    def __init__(self, input_tys: list[GuppyType], output_ty: GuppyType) -> None:
        super().__init__([])
        self.input_tys = input_tys
        self.output_ty = output_ty


def check_cfg(
    cfg: CFG, inputs: VarRow, return_ty: GuppyType, globals: Globals
) -> CheckedCFG:
    """Type checks a control-flow graph.

    Annotates the basic blocks with input and output type signatures and removes
    unreachable blocks.
    """
    raise NotImplementedError


def check_bb(
    bb: BB,
    checked_cfg: CheckedCFG,
    inputs: VarRow,
    return_ty: GuppyType,
    globals: Globals,
) -> CheckedBB:
    raise NotImplementedError
