from dataclasses import dataclass
from typing import ClassVar

from guppylang_internals.diagnostic import Error, Note


@dataclass(frozen=True)
class UnsupportedError(Error):
    title: ClassVar[str] = "Unsupported"
    span_label: ClassVar[str] = "{things} {is_are} not supported{extra}"
    things: str
    singular: bool = False
    unsupported_in: str = ""

    @property
    def is_are(self) -> str:
        return "is" if self.singular else "are"

    @property
    def extra(self) -> str:
        return f" in {self.unsupported_in}" if self.unsupported_in else ""


@dataclass(frozen=True)
class UnexpectedError(Error):
    title: ClassVar[str] = "Unexpected {things}"
    span_label: ClassVar[str] = "Unexpected {things}{extra}"
    things: str
    unexpected_in: str = ""

    @property
    def extra(self) -> str:
        return f" in {self.unexpected_in}" if self.unexpected_in else ""


@dataclass(frozen=True)
class ExpectedError(Error):
    title: ClassVar[str] = "Expected {things}"
    span_label: ClassVar[str] = "Expected {things}{extra}"
    things: str
    got: str = ""

    @property
    def extra(self) -> str:
        return f", got {self.got}" if self.got else ""


@dataclass(frozen=True)
class ReturnUnderModifierError(Error):
    title: ClassVar[str] = "Unexpected return"
    span_label: ClassVar[str] = "Return statement found in a with block"


@dataclass(frozen=True)
class LoopCtrlUnderModifierError(Error):
    title: ClassVar[str] = "Unexpected loop control"
    span_label: ClassVar[str] = "{kind} found in a with block"
    kind: str


@dataclass(frozen=True)
class AssignUnderDagger(Error):
    title: ClassVar[str] = "Assignment in dagger"
    span_label: ClassVar[str] = "Assignment found in a dagger context"

    @dataclass(frozen=True)
    class Modifier(Note):
        span_label: ClassVar[str] = "dagger modifier is used here"


# TODO: It might be better to merge this error with AssignUnderDagger
@dataclass(frozen=True)
class LoopUnderDagger(Error):
    title: ClassVar[str] = "Loop in dagger"
    span_label: ClassVar[str] = "Loop found in a dagger context"

    @dataclass(frozen=True)
    class Dagger(Note):
        span_label: ClassVar[str] = "dagger modifier is used here"
