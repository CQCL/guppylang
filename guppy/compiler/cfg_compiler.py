from guppy.checker.cfg_checker import CheckedBB, CheckedCFG
from guppy.compiler.core import CompiledGlobals
from guppy.hugr.hugr import Hugr, Node, CFNode


def compile_cfg(
    cfg: CheckedCFG, graph: Hugr, parent: Node, globals: CompiledGlobals
) -> None:
    """Compiles a CFG to Hugr."""
    raise NotImplementedError


def compile_bb(
    bb: CheckedBB, graph: Hugr, parent: Node, globals: CompiledGlobals
) -> CFNode:
    """Compiles a single basic block to Hugr."""
    raise NotImplementedError
