import ast
import functools
import sys
import textwrap
from dataclasses import dataclass, field
from typing import Optional, Any, Sequence, Callable, TypeVar, cast

from guppy.ast_util import AstNode, get_line_offset, get_file, get_source
from guppy.types import GuppyType, FunctionType
from guppy.hugr.hugr import OutPortV, Node


# Whether the interpreter should exit when a Guppy error occurs
EXIT_ON_ERROR: bool = True


@dataclass(frozen=True)
class SourceLoc:
    """A source location associated with an AST node.

    This class translates the location data provided by the ast module into a location
    inside the file.
    """

    file: str
    line: int
    col: int
    ast_node: Optional[AstNode]

    @staticmethod
    def from_ast(node: AstNode) -> "SourceLoc":
        file, line_offset = get_file(node), get_line_offset(node)
        assert file is not None and line_offset is not None
        return SourceLoc(file, line_offset + node.lineno - 1, node.col_offset, node)

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
    locs_in_msg: Sequence[Optional[AstNode]] = field(default_factory=list)

    def get_msg(self) -> str:
        """Returns the message associated with this error.

        A line offset is needed to translate AST locations mentioned in the message into
        source locations in the actual file."""
        return self.raw_msg.format(
            *(
                SourceLoc.from_ast(loc) if loc is not None else "???"
                for loc in self.locs_in_msg
            )
        )


class GuppyTypeError(GuppyError):
    """Special Guppy exception for type errors."""

    pass


class InternalGuppyError(Exception):
    """Exception for internal problems during compilation."""

    pass


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


class UnknownFunctionType(FunctionType):
    """Dummy function type for custom functions without an expressible type.

    Raises an `InternalGuppyError` if one tries to access one of its members.
    """

    def __init__(self) -> None:
        pass

    @property
    def args(self) -> Sequence[GuppyType]:
        raise InternalGuppyError("Tried to access unknown function type")

    @property
    def returns(self) -> GuppyType:
        raise InternalGuppyError("Tried to access unknown function type")

    @property
    def args_names(self) -> Optional[Sequence[str]]:
        raise InternalGuppyError("Tried to access unknown function type")


def format_source_location(
    loc: ast.AST,
    num_lines: int = 3,
    indent: int = 4,
) -> str:
    """Creates a pretty banner to show source locations for errors."""
    source, line_offset = get_source(loc), get_line_offset(loc)
    assert source is not None and line_offset is not None
    source_lines = source.splitlines(keepends=True)
    end_col_offset = loc.end_col_offset or len(source_lines[loc.lineno])
    s = "".join(source_lines[max(loc.lineno - num_lines, 0) : loc.lineno]).rstrip()
    s += "\n" + loc.col_offset * " " + (end_col_offset - loc.col_offset) * "^"
    s = textwrap.dedent(s).splitlines()
    # Add line numbers
    line_numbers = [
        str(line_offset + loc.lineno - i) + ":" for i in range(num_lines, 0, -1)
    ]
    longest = max(len(ln) for ln in line_numbers)
    prefixes = [ln + " " * (longest - len(ln) + indent) for ln in line_numbers]
    res = "".join(prefix + line + "\n" for prefix, line in zip(prefixes, s[:-1]))
    res += (longest + indent) * " " + s[-1]
    return res


FuncT = TypeVar("FuncT", bound=Callable[..., Any])


def pretty_errors(f: FuncT) -> FuncT:
    """Decorator to print custom error banners when a `GuppyError` occurs."""

    @functools.wraps(f)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        try:
            return f(*args, **kwargs)
        except GuppyError as err:
            # Reraise if we're missing a location
            if not err.location:
                raise err
            loc = err.location
            file, line_offset = get_file(loc), get_line_offset(loc)
            assert file is not None and line_offset is not None
            line = line_offset + loc.lineno - 1
            print(
                f"Guppy compilation failed. Error in file {file}:{line}\n\n"
                f"{format_source_location(loc)}\n"
                f"{err.__class__.__name__}: {err.get_msg()}",
                file=sys.stderr,
            )
            if EXIT_ON_ERROR:
                sys.exit(1)
            return None

    return cast(FuncT, wrapped)
