import string
import textwrap
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import (
    Any,
    ClassVar,
    Final,
    Literal,
    Protocol,
    overload,
    runtime_checkable,
)

from typing_extensions import Self

from guppylang.error import InternalGuppyError
from guppylang.span import Loc, SourceMap, Span, ToSpan, to_span


class DiagnosticLevel(Enum):
    """Severity levels for compiler diagnostics."""

    #: An error that makes it impossible to proceed, causing an immediate abort.
    FATAL = auto()

    #: A regular error that is encountered during compilation. This is the most common
    #: diagnostic case.
    ERROR = auto()

    #: A warning about the code being compiled. Doesn't prevent compilation from
    #: finishing.
    WARNING = auto()

    #: A message giving some additional context. Usually used as a sub-diagnostic of
    #: errors.
    NOTE = auto()

    #: A message suggesting how to fix something. Usually used as a sub-diagnostic of
    #: errors.
    HELP = auto()


@runtime_checkable
@dataclass(frozen=True)
class SubDiagnostic(Protocol):
    """A sub-diagnostic attached to a parent diagnostic.

    Can be used to give some additional context, for example a note attached to an
    error.
    """

    #: Severity level of the sub-diagnostic.
    level: ClassVar[DiagnosticLevel]

    #: Optional span of the source location associated with this sub-diagnostic.
    span: ToSpan | None

    #: Label that is printed next to the span highlight. Can only be used if a span is
    #: provided.
    span_label: ClassVar[str | None] = None

    #: Message that is printed if no span is provided.
    message: ClassVar[str | None] = None

    #: The parent main diagnostic this sub-diagnostic is attached to.
    _parent: "Diagnostic | None" = field(default=None, init=False)

    def __post_init__(self) -> None:
        if self.span_label and self.span is None:
            raise InternalGuppyError("SubDiagnostic: Span label provided without span")

    @property
    def rendered_message(self) -> str | None:
        """The message of this diagnostic with formatted placeholders if provided."""
        return self._render(self.message)

    @property
    def rendered_span_label(self) -> str | None:
        """The span label of this diagnostic with formatted placeholders if provided."""
        return self._render(self.span_label)

    @overload
    def _render(self, s: str) -> str: ...

    @overload
    def _render(self, s: None) -> None: ...

    def _render(self, s: str | None) -> str | None:
        """Helper method to fill in placeholder values in strings with fields of this
        diagnostic.
        """

        class CustomFormatter(string.Formatter):
            def get_value(
                _self, key: int | str, args: Sequence[Any], kwargs: Mapping[str, Any]
            ) -> Any:
                assert isinstance(key, str)
                if hasattr(self, key):
                    return getattr(self, key)
                return getattr(self._parent, key)

        return CustomFormatter().format(s) if s is not None else None


@runtime_checkable
@dataclass(frozen=True)
class Diagnostic(SubDiagnostic, Protocol):
    """Abstract base class for compiler diagnostics that are reported to users.

    These could be fatal errors, regular errors, or warnings (see `DiagnosticLevel`).
    """

    #: Short title for the diagnostic that is displayed at the top.
    title: ClassVar[str]

    #: Optional sub-diagnostics giving some additional context.
    children: list["SubDiagnostic"] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.span is None and self.children:
            raise InternalGuppyError(
                "Diagnostic: Span-less diagnostics can't have children (FIXME)"
            )

    @property
    def rendered_title(self) -> str:
        """The title of this diagnostic with formatted placeholders."""
        return self._render(self.title)

    def add_sub_diagnostic(self, sub: "SubDiagnostic") -> Self:
        """Adds a new sub-diagnostic."""
        if (
            self.span is not None
            and sub.span is not None
            and to_span(sub.span).file != to_span(self.span).file
        ):
            raise InternalGuppyError(
                "Diagnostic: Cross-file sub-diagnostics are not supported"
            )
        object.__setattr__(sub, "_parent", self)
        self.children.append(sub)
        return self

    @property
    def rendered_message(self) -> str | None:
        """The message of this diagnostic with formatted placeholders if provided."""
        return self._render(self.message)

    @property
    def rendered_span_label(self) -> str | None:
        """The span label of this diagnostic with formatted placeholders if provided."""
        return self._render(self.span_label)


@runtime_checkable
@dataclass(frozen=True)
class Fatal(Diagnostic, Protocol):
    """Compiler diagnostic for errors that makes it impossible to proceed, causing an
    immediate abort."""

    level: ClassVar[Literal[DiagnosticLevel.FATAL]] = DiagnosticLevel.FATAL


@runtime_checkable
@dataclass(frozen=True)
class Error(Diagnostic, Protocol):
    """Compiler diagnostic for regular errors that are encountered during
    compilation."""

    level: ClassVar[Literal[DiagnosticLevel.ERROR]] = DiagnosticLevel.ERROR


@runtime_checkable
@dataclass(frozen=True)
class Note(SubDiagnostic, Protocol):
    """Compiler sub-diagnostic giving some additional context."""

    level: ClassVar[Literal[DiagnosticLevel.NOTE]] = DiagnosticLevel.NOTE


@runtime_checkable
@dataclass(frozen=True)
class Help(SubDiagnostic, Protocol):
    """Compiler sub-diagnostic suggesting how to fix something."""

    level: ClassVar[Literal[DiagnosticLevel.HELP]] = DiagnosticLevel.HELP


class DiagnosticsRenderer:
    """Standard renderer for compiler diagnostics in human-readable format."""

    source: SourceMap
    buffer: list[str]

    #: Maximum amount of leading whitespace until we start trimming it
    MAX_LEADING_WHITESPACE: Final[int] = 12

    #: Amount of leading whitespace left after trimming for padding
    OPTIMAL_LEADING_WHITESPACE: Final[int] = 4

    #: Maximum length of span labels after which we insert a newline
    MAX_LABEL_LINE_LEN: Final[int] = 60

    #: Maximum length of messages after which we insert a newline
    MAX_MESSAGE_LINE_LEN: Final[int] = 80

    #: Number of preceding source lines we show to give additional context
    PREFIX_CONTEXT_LINES: Final[int] = 2

    def __init__(self, source: SourceMap) -> None:
        self.buffer = []
        self.source = source

    def render_diagnostic(self, diag: Diagnostic) -> None:
        """Renders a single diagnostic together with its sub-diagnostics.

        Example:

        ```
        Error: Short title for the diagnostic (at path/to/file.py:line:column)
           |
        42 | def foo(x: blah) -> None:
           |            ^^^^ Span label
           |
        55 |     x = bar() + baz
           |         ----- Sub-diagnostic label

        Longer message describing the error.

        note: Sub-diagnostic message without span
        ```
        """
        if diag.span is None:
            # Omit the title if we don't have a span, but a long message. This case
            # should be fairly rare.
            msg = diag.rendered_message or diag.rendered_title
            self.buffer += wrap(
                f"{self.level_str(diag.level)}: {msg}", self.MAX_MESSAGE_LINE_LEN
            )
        else:
            span = to_span(diag.span)
            level = self.level_str(diag.level)
            all_spans = [span] + [
                to_span(child.span) for child in diag.children if child.span
            ]
            max_lineno = max(s.end.line for s in all_spans)
            self.buffer.append(f"{level}: {diag.rendered_title} (at {span.start})")
            self.render_snippet(
                span,
                diag.rendered_span_label,
                max_lineno,
                is_primary=True,
                prefix_lines=self.PREFIX_CONTEXT_LINES,
            )
            # First render all sub-diagnostics that come with a span
            for sub_diag in diag.children:
                if sub_diag.span:
                    self.render_snippet(
                        to_span(sub_diag.span),
                        sub_diag.rendered_span_label,
                        max_lineno,
                        is_primary=False,
                    )
            if diag.rendered_message:
                self.buffer.append("")
                self.buffer += wrap(diag.rendered_message, self.MAX_MESSAGE_LINE_LEN)
        # Finally, render all sub-diagnostics that have a non-span message
        for sub_diag in diag.children:
            if sub_diag.rendered_message:
                self.buffer.append("")
                self.buffer += wrap(
                    f"{self.level_str(sub_diag.level)}: {sub_diag.rendered_message}",
                    self.MAX_MESSAGE_LINE_LEN,
                )

    def render_snippet(
        self,
        span: Span,
        label: str | None,
        max_lineno: int,
        is_primary: bool,
        prefix_lines: int = 0,
    ) -> None:
        """Renders the source associated with a span together with an optional label.

        ```
           |
        42 | def foo(x: blah) -> None:
           |            ^^^^ Span label. This could cover
           |                 multiple lines!
        ```

        Also supports spans covering multiple lines:

        ```
           |
        42 | def foo(x: int) -> None:
           | ^^^^^^^^^^^^^^^^^^^^^^^^
           | ...
        48 |     return bar()
           | ^^^^^^^^^^^^^^^^ Label covering the entire definition of foo
        ```

        If `is_primary` is `False`, the span is highlighted using `-` instead of `^`:

        ```
           |
        42 | def foo(x: blah) -> None:
           |            ---- Non-primary span label
        ```

        Optionally includes up to `prefix_lines` preceding source lines to give
        additional context.
        """
        # Check how much space we need to reserve for the leading line numbers
        ll_length = len(str(max_lineno))
        highlight_char = "^" if is_primary else "-"

        def render_line(line: str, line_number: int | None = None) -> None:
            """Helper method to render a line with the line number bar on the left."""
            ll = "" if line_number is None else str(line_number)
            self.buffer.append(" " * (ll_length - len(ll)) + ll + " | " + line)

        # One line of padding
        render_line("")

        # Grab all lines we want to display and remove excessive leading whitespace
        prefix_lines = min(prefix_lines, span.start.line - 1)
        all_lines = self.source.span_lines(span, prefix_lines)
        leading_whitespace = min(len(line) - len(line.lstrip()) for line in all_lines)
        if leading_whitespace > self.MAX_LEADING_WHITESPACE:
            remove = leading_whitespace - self.OPTIMAL_LEADING_WHITESPACE
            all_lines = [line[remove:] for line in all_lines]
            span = span.shift_left(remove)

        # Render prefix lines
        for i, line in enumerate(all_lines[:prefix_lines]):
            render_line(line, span.start.line - prefix_lines + i)
        span_lines = all_lines[prefix_lines:]

        if span.is_multiline:
            [first, *middle, last] = span_lines
            render_line(first, span.start.line)
            # Compute the subspan that only covers the first line and render its
            # highlight banner
            first_span = Span(span.start, Loc(span.file, span.start.line, len(first)))
            first_highlight = " " * first_span.start.column + highlight_char * len(
                first_span
            )
            render_line(first_highlight)
            # Omit everything in the middle
            if middle:
                render_line("...")
            # The last line is handled uniformly with the single-line case below.
            # Therefore, create a subspan that only covers the last line.
            last_span = Span(Loc(span.file, span.end.line, 0), span.end)
        else:
            [last] = span_lines
            last_span = span

        # Render the last span line and add highlights
        render_line(last, span.end.line)
        last_highlight = " " * last_span.start.column + highlight_char * len(last_span)

        # Render the label next to the highlight
        if label:
            [label_first, *label_rest] = wrap(
                label,
                self.MAX_LABEL_LINE_LEN,
                # One space after the last `^`
                initial_indent=" ",
                # Indent all subsequent lines to be aligned
                subsequent_indent=" " * (len(last_highlight) + 1),
            )
            render_line(last_highlight + label_first)
            for lbl in label_rest:
                render_line(lbl)
        else:
            render_line(last_highlight)

    @staticmethod
    def level_str(level: DiagnosticLevel) -> str:
        """Returns the text used to identify the different kinds of diagnostics."""
        return level.name.lower().capitalize()


def wrap(text: str, width: int, **kwargs: Any) -> list[str]:
    """Custom version of `textwrap.wrap` that correctly handles text with line breaks.

    Even with `replace_whitespace=False`, the original version doesn't count line breaks
    as new paragraphs and instead would produce bad results like

    ```
    short paragraph of text

    long paragraph of text xxxxx                             # broken too early :(
    xxxx xxxxxx xxxx xxxxx xxxxxxxx xxxxxxxxxxxx xxxxx xx
    xxxx xxxxxxx xxxxx xx xxxx xxxxxxx xxxx
    ```
    """
    return [
        line
        for paragraph in text.splitlines()
        for line in (textwrap.wrap(paragraph, width, **kwargs) if paragraph else [""])
    ]
