import ast
import itertools
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar, TypeAlias

from guppylang.hugr.hugr import Hugr, Node

if TYPE_CHECKING:
    from guppylang.checker.core import Globals
    from guppylang.compiler.core import CompiledGlobals
    from guppylang.module import GuppyModule


RawDef: TypeAlias = "ParsableDef | ParsedDef"
ParsedDef: TypeAlias = "CheckableDef | CheckedDef"
CheckedDef: TypeAlias = "CompilableDef | CompiledDef"


@dataclass(frozen=True)
class DefId:
    """Unique identifier for definitions across modules.

    This id is persistent across all compilation stages. It can be used to identify a
    definition at any step in the compilation pipeline.
    """

    id: int
    module: "GuppyModule | None" = field(compare=False, hash=False)

    _ids: ClassVar[Iterator[int]] = itertools.count()

    @classmethod
    def fresh(cls, module: "GuppyModule | None" = None) -> "DefId":
        return DefId(next(cls._ids), module)


@dataclass(frozen=True)
class Definition(ABC):
    """Abstract base class for user-defined objects on module-level.

    Each definition is identified by a globally unique id. Furthermore, we store the
    user-picked name for the defined object and an optional AST node for the definition
    location.
    """

    id: DefId
    name: str
    defined_at: ast.FunctionDef | None

    @property
    @abstractmethod
    def description(self) -> str:
        """ """


class ParsableDef(Definition, ABC):
    """Abstract base class for raw definitions that still require parsing.

    For example, raw function definitions first need to parse their signature and check
    that all types are valid. The result of parsing should be a definition that is ready
    to be checked.
    """

    @abstractmethod
    def parse(self, globals: "Globals") -> ParsedDef:
        """Performs parsing and validation, returning a definition that can be checked.

        The provided globals contain all other raw definitions that have been defined.
        """


class CheckableDef(Definition, ABC):
    """Abstract base class for definitions that still need to be checked.

    The result of checking should be a definition that is ready to be compiled to Hugr.
    """

    @abstractmethod
    def check(self, globals: "Globals") -> CheckedDef:
        """Type checks the definition.

        The provided globals contain all other parsed definitions that have been
        defined.

        Returns a checked version of the definition that can be compiled to Hugr.
        """


class CompilableDef(Definition, ABC):
    """Abstract base class for definitions that still need to be compiled to Hugr.

    The result of compilation should be a `CompiledDef` with a pointer to the Hugr node
    that was created for this definition.
    """

    @abstractmethod
    def compile(self, graph: Hugr, parent: Node) -> "CompiledDef":
        """Adds a Hugr node for the definition to the provided graph.

        Note that is not required to fill in the contents of the node. At this point,
        we don't have access to the globals since they have not all been compiled yet.

        See `CompiledDef.compile_contents()` for the hook to compile the inside of the
        node. This two-step process enables things like mutual recursion.
        """


class CompiledDef(Definition, ABC):
    """Abstract base class for definitions that have been added to a Hugr."""

    def compile_contents(self, graph: Hugr, globals: "CompiledGlobals") -> None:
        """Optional hook that is called to fill in the content of the Hugr node.

        Opposed to `CompilableDef.compile()`, we have access to all other compiled
        definitions here, which allows things like mutual recursion.
        """
