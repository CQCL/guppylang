from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Literal

from typing_extensions import Self

from guppylang.error import InternalGuppyError
from guppylang.span import ToSpan


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


@dataclass(frozen=True)
class Diagnostic:
    """Abstract base class for compiler diagnostics that are reported to users.

    These could be fatal errors, regular errors, or warnings (see `DiagnosticLevel`).
    """

    #: Severity level of the diagnostic.
    level: DiagnosticLevel

    #: Primary span of the source location associated with this diagnostic. The span
    #: is optional, but provided in almost all cases.
    span: ToSpan | None = field(default=None, init=False)

    #: Short title for the diagnostic that is displayed at the top.
    title: str | None = field(default=None, init=False)

    #: Label that is printed below the span.
    label: str | None = field(default=None, init=False)

    #: Label that is printed next to the span highlight. Can only be used if a span is
    #: provided.
    span_label: str | None = field(default=None, init=False)

    #: Optional sub-diagnostics giving some additional context.
    children: list["SubDiagnostic"] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        if self.span_label and not self.span:
            raise InternalGuppyError("Diagnostic: Span label provided without span")

    def add_sub_diagnostic(self, sub: "SubDiagnostic") -> Self:
        """Adds a new sub-diagnostic."""
        self.children.append(sub)
        return self


@dataclass(frozen=True)
class SubDiagnostic:
    """A sub-diagnostic attached to a parent diagnostic.

    Can be used to give some additional context, for example a note attached to an
    error.
    """

    #: Severity level of the sub-diagnostic.
    level: DiagnosticLevel

    #: Optional span of the source location associated with this sub-diagnostic.
    span: ToSpan | None = field(default=None, init=False)

    #: Short title for the diagnostic that is displayed at the top.
    title: str | None = field(default=None, init=False)

    #: Label that is printed below the span.
    label: str | None = field(default=None, init=False)

    #: Label that is printed next to the span highlight. Can only be used if a span is
    #: provided.
    span_label: str | None = field(default=None, init=False)


@dataclass(frozen=True)
class Error(Diagnostic):
    """Compiler diagnostic for regular error that are encountered during compilation."""

    level: Literal[DiagnosticLevel.ERROR] = field(
        default=DiagnosticLevel.ERROR, init=False
    )
