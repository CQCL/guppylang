import ast
import inspect
import textwrap
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import hugr.build.function as hf
import hugr.tys as ht
from hugr.build.dfg import DefinitionBuilder, OpVar


from guppylang.checker.core import Globals, PyScope
from guppylang.definition.common import (
    CheckableDef,
    CompilableDef,
    ParsableDef,
)
from guppylang.definition.value import CompiledCallableDef
from guppylang.error import GuppyError
from guppylang.span import SourceMap

PyFunc = Callable[..., Any]

@dataclass(frozen=True)
class RawPytketDef(ParsableDef):
    """A raw function stub definition describing the signature of a circuit.

    Args:
        id: The unique definition identifier.
        name: The name of the function stub.
        defined_at: The AST node where the stub was defined.
        python_func: The Python function stub.
        python_scope: The Python scope where the function stub was defined.
    """

    python_func: PyFunc
    python_scope: PyScope

    description: str = field(default="pytket circuit", init=False)

    def parse(self, globals: Globals, sources: SourceMap) -> "ParsedPytketDef":
        """Parses and checks the user-provided signature matches the user-provided circuit."""
        pass


@dataclass(frozen=True)
class ParsedPytketDef(CheckableDef, CompilableDef):
    """A circuit definition with parsed and checked signature.

    Args:
        id: The unique definition identifier.
        name: The name of the function.
        defined_at: The AST node where the function was defined.
        ty: The type of the function.
        python_scope: The Python scope where the function was defined.
    """

    description: str = field(default="pytket circuit", init=False)

    def compile_outer(self, module: DefinitionBuilder[OpVar]) -> "CompiledPytketDef":
        """Adds a Hugr `FuncDefn` node for this function to the Hugr."""
        pass


class CompiledPytketDef(CompiledCallableDef):
    """A function definition with a corresponding Hugr node.

    Args:
        id: The unique definition identifier.
        name: The name of the function.
        defined_at: The AST node where the function was defined.
        ty: The type of the function.
        python_scope: The Python scope where the function was defined.
        func_df: The Hugr function definition.
    """

    func_def: hf.Function