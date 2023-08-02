import ast
from dataclasses import dataclass, field
from typing import Optional, Union, Any, Sequence

from guppy.ast_util import AstNode
from guppy.guppy_types import GuppyType, IntType, FloatType, BoolType
from guppy.hugr.hugr import OutPortV, Node


@dataclass(frozen=True)
class SourceLoc:
    """A source location associated with an AST node.

    This class translates the location data provided by the ast module into a location
    inside the file.
    """

    line: int
    col: int
    ast_node: Optional[AstNode]

    @staticmethod
    def from_ast(node: AstNode, line_offset: int) -> "SourceLoc":
        return SourceLoc(line_offset + node.lineno, node.col_offset, node)

    def __str__(self) -> str:
        return f"{self.line}:{self.col}"

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, SourceLoc):
            return NotImplemented
        return (self.line, self.col) < (other.line, other.col)


@dataclass
class GuppyError(Exception):
    """General Guppy error tied to a node in the AST.

    The error message can also refer to AST locations using format placeholders `{0}`,
    `{1}`, etc. and passing the corresponding AST nodes to `locs_in_msg`."""

    raw_msg: str
    location: Optional[AstNode] = None
    # The message can also refer to AST locations using format placeholders `{0}`, `{1}`
    locs_in_msg: Sequence[AstNode] = field(default_factory=list)

    def get_msg(self, line_offset: int) -> str:
        """Returns the message associated with this error.

        A line offset is needed to translate AST locations mentioned in the message into
        source locations in the actual file."""
        return self.raw_msg.format(
            *(SourceLoc.from_ast(l, line_offset) for l in self.locs_in_msg)
        )


class GuppyTypeError(GuppyError):
    """Special Guppy exception for type errors."""

    pass


class InternalGuppyError(Exception):
    """Exception for internal problems during compilation."""

    pass


def assert_arith_type(ty: GuppyType, node: ast.expr) -> None:
    """Check that a given type is arithmetic, i.e. an integer or float,
    or raise a type error otherwise."""
    if not isinstance(ty, IntType) and not isinstance(ty, FloatType):
        raise GuppyTypeError(
            f"Expected expression of type `int` or `float`, "
            f"but got `{ast.unparse(node)}` of type `{ty}`",
            node,
        )


def assert_int_type(ty: GuppyType, node: ast.expr) -> None:
    """Check that a given type is integer or raise a type error otherwise."""
    if not isinstance(ty, IntType):
        raise GuppyTypeError(
            f"Expected expression of type `int`, "
            f"but got `{ast.unparse(node)}` of type `{ty}`",
            node,
        )


def assert_bool_type(ty: GuppyType, node: ast.expr) -> None:
    """Check that a given type is boolean or raise a type error otherwise."""
    if not isinstance(ty, BoolType):
        raise GuppyTypeError(
            f"Expected expression of type `bool`, "
            f"but got `{ast.unparse(node)}` of type `{ty}`",
            node,
        )


class UndefinedPort(OutPortV):
    """Dummy port for undefined variables.

    Raises an `InternalGuppyError` if one tries to access one of its properties.
    """

    def __init__(self, ty: GuppyType):
        self._ty = ty

    @property
    def ty(self) -> GuppyType:
        return self._ty

    @property
    def node(self) -> Node:
        raise InternalGuppyError("Tried to access undefined Port")

    @property
    def offset(self) -> int:
        raise InternalGuppyError("Tried to access undefined Port")
