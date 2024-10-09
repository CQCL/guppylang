from dataclasses import dataclass, field
from enum import Enum, auto
from typing import ClassVar, Literal, Protocol, runtime_checkable

from typing_extensions import Self

from guppylang.error import InternalGuppyError
from guppylang.span import ToSpan, to_span


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
class Diagnostic(Protocol):
    """Abstract base class for compiler diagnostics that are reported to users.

    These could be fatal errors, regular errors, or warnings (see `DiagnosticLevel`).
    """

    #: Severity level of the diagnostic.
    level: ClassVar[DiagnosticLevel]

    #: Primary span of the source location associated with this diagnostic. The span
    #: is optional, but provided in almost all cases.
    span: ToSpan | None

    #: Short title for the diagnostic that is displayed at the top.
    title: ClassVar[str]

    #: Longer message that is printed below the span.
    long_message: ClassVar[str | None] = None

    #: Label that is printed next to the span highlight. Can only be used if a span is
    #: provided.
    span_label: ClassVar[str | None] = None

    #: Optional sub-diagnostics giving some additional context.
    children: list["SubDiagnostic"] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        if self.span_label and not self.span:
            raise InternalGuppyError("Diagnostic: Span label provided without span")

    def add_sub_diagnostic(self, sub: "SubDiagnostic") -> Self:
        """Adds a new sub-diagnostic."""
        if self.span and sub.span and to_span(sub.span).file != to_span(self.span).file:
            raise InternalGuppyError(
                "Diagnostic: Cross-file sub-diagnostics are not supported"
            )
        self.children.append(sub)
        return self


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

    def __post_init__(self) -> None:
        if self.span_label and not self.span:
            raise InternalGuppyError("SubDiagnostic: Span label provided without span")
        if not self.span and not self.message:
            raise InternalGuppyError("SubDiagnostic: Empty diagnostic")


@runtime_checkable
@dataclass(frozen=True)
class Error(Diagnostic, Protocol):
    """Compiler diagnostic for regular errors that are encountered during compilation."""

    level: ClassVar[Literal[DiagnosticLevel.ERROR]] = DiagnosticLevel.ERROR
