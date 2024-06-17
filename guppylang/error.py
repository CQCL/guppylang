import ast
import functools
import os
import sys
import textwrap
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from types import TracebackType
from typing import Any, TypeVar, cast

from guppylang.ast_util import AstNode, get_file, get_line_offset, get_source


@dataclass(frozen=True)
class SourceLoc:
    """A source location associated with an AST node.

    This class translates the location data provided by the ast module into a location
    inside the file.
    """

    file: str
    line: int
    col: int
    ast_node: AstNode | None

    @staticmethod
    def from_ast(node: AstNode) -> "SourceLoc":
        file, line_offset = get_file(node), get_line_offset(node)
        assert file is not None
        assert line_offset is not None
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
    location: AstNode | None = None
    # The message can also refer to AST locations using format placeholders `{0}`, `{1}`
    locs_in_msg: Sequence[AstNode | None] = field(default_factory=list)

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


class GuppyTypeInferenceError(GuppyError):
    """Special Guppy exception for type inference errors."""


class MissingModuleError(GuppyError):
    """Special Guppy exception for operations that require a guppy module."""


class InternalGuppyError(Exception):
    """Exception for internal problems during compilation."""


ExceptHook = Callable[[type[BaseException], BaseException, TracebackType | None], Any]


@contextmanager
def exception_hook(hook: ExceptHook) -> Iterator[None]:
    """Sets a custom `excepthook` for the scope of a 'with' block."""
    old_hook = sys.excepthook
    sys.excepthook = hook
    yield
    sys.excepthook = old_hook


def format_source_location(
    loc: ast.AST,
    num_lines: int = 3,
    indent: int = 4,
) -> str:
    """Creates a pretty banner to show source locations for errors."""
    source, line_offset = get_source(loc), get_line_offset(loc)
    assert source is not None
    assert line_offset is not None
    source_lines = source.splitlines(keepends=True)
    end_col_offset = loc.end_col_offset
    if end_col_offset is None or (loc.end_lineno and loc.end_lineno > loc.lineno):
        end_col_offset = len(source_lines[loc.lineno - 1]) - 1
    s = "".join(source_lines[max(loc.lineno - num_lines, 0) : loc.lineno]).rstrip()
    s += "\n" + loc.col_offset * " " + (end_col_offset - loc.col_offset) * "^"
    s = textwrap.dedent(s).splitlines()
    # Add line numbers
    line_numbers = [
        str(line_offset + loc.lineno - i) + ":" for i in range(num_lines, 0, -1)
    ]
    longest = max(len(ln) for ln in line_numbers)
    prefixes = [ln + " " * (longest - len(ln) + indent) for ln in line_numbers]
    res = "".join(prefix + line + "\n" for prefix, line in zip(prefixes, s[:-1], strict=False))
    res += (longest + indent) * " " + s[-1]
    return res


FuncT = TypeVar("FuncT", bound=Callable[..., Any])


def pretty_errors(f: FuncT) -> FuncT:
    """Decorator to print custom error banners when a `GuppyError` occurs."""

    def hook(
        excty: type[BaseException], err: BaseException, traceback: TracebackType | None
    ) -> None:
        """Custom `excepthook` that intercepts `GuppyExceptions` for pretty printing."""
        # Fall back to default hook if it's not a GuppyException or we're missing an
        # error location
        if not isinstance(err, GuppyError) or err.location is None:
            sys.__excepthook__(excty, err, traceback)
            return

        loc = err.location
        file, line_offset = get_file(loc), get_line_offset(loc)
        assert file is not None
        assert line_offset is not None
        line = line_offset + loc.lineno - 1
        sys.stderr.write(
            f"Guppy compilation failed. Error in file {file}:{line}\n\n"
            f"{format_source_location(loc)}\n"
            f"{err.__class__.__name__}: {err.get_msg()}\n",
        )

    @functools.wraps(f)
    def pretty_errors_wrapped(*args: Any, **kwargs: Any) -> Any:
        with exception_hook(hook):
            try:
                return f(*args, **kwargs)
            except GuppyError as err:
                # For normal usage, this `try` block is not necessary since the
                # excepthook is automatically invoked when the exception (which is being
                # reraised below) is not handled. However, when running tests, we have
                # to manually invoke the hook to print the error message, since the
                # tests always have to capture exceptions.
                if _pytest_running():
                    hook(type(err), err, err.__traceback__)
                raise

    return cast(FuncT, pretty_errors_wrapped)


def _pytest_running() -> bool:
    """Checks if we are currently running pytest.

    See https://docs.pytest.org/en/latest/example/simple.html#pytest-current-test-environment-variable
    """
    return "PYTEST_CURRENT_TEST" in os.environ
