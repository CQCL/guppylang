"""Source spans representing locations in the code being compiled."""

import ast
from dataclasses import dataclass
from typing import TypeAlias

from guppylang.ast_util import get_file, get_line_offset
from guppylang.error import InternalGuppyError


@dataclass(frozen=True, order=True)
class Loc:
    """A location in a source file."""

    file: str

    #: Line number starting at 1
    line: int

    #: Column number starting at 1
    column: int


@dataclass(frozen=True)
class Span:
    """A continuous sequence of source code within a file."""

    #: Starting location of the span (inclusive)
    start: Loc

    # Ending location of the span (exclusive)
    end: Loc

    def __post_init__(self) -> None:
        if self.start.file != self.end.file:
            raise InternalGuppyError("Span: Source spans multiple files")
        if self.start > self.end:
            raise InternalGuppyError("Span: Start after end")

    def __contains__(self, x: "Span | Loc") -> bool:
        """Determines whether another span or location is completely contained in this
        span."""
        if self.file != x.file:
            return False
        if isinstance(x, Span):
            return self.start <= x.start <= self.end <= x.end
        return self.start <= x <= self.end

    def __and__(self, other: "Span") -> "Span | None":
        """Returns the intersection with the given span or `None` if they don't
        intersect."""
        if self.file != other.file:
            return None
        if self.start > other.end or other.start > self.end:
            return None
        return Span(max(self.start, other.start), min(self.end, other.end))

    @property
    def file(self) -> str:
        """The file containing this span."""
        return self.start.file


#: Objects in the compiler that are associated with a source span
ToSpan: TypeAlias = ast.AST | Span


def to_span(x: ToSpan) -> Span:
    """Extracts a source span from an object."""
    if isinstance(x, Span):
        return x
    file, line_offset = get_file(x), get_line_offset(x)
    assert file is not None
    assert line_offset is not None
    # line_offset starts at 1, so we have to do subtract 1
    start = Loc(file, x.lineno + line_offset - 1, x.col_offset)
    end = Loc(
        file,
        (x.end_lineno or x.lineno) + line_offset - 1,
        x.end_col_offset or x.col_offset,
    )
    return Span(start, end)
