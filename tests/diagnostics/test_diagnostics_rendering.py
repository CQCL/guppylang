"""Snapshot tests for diagnostics rendering"""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from guppylang.diagnostic import (
    Diagnostic,
    DiagnosticsRenderer,
    Error,
    Help,
    Note,
)
from guppylang.span import Loc, SourceMap, Span

file = "<unknown>"


def run_test(source: str, diagnostic: Diagnostic, snapshot, request):
    sources = SourceMap()
    sources.add_file(file, source)

    renderer = DiagnosticsRenderer(sources)
    renderer.render_diagnostic(diagnostic)
    out = "\n".join(renderer.buffer)

    snapshot.snapshot_dir = str(Path(request.fspath).parent / "snapshots")
    snapshot.assert_match(out, f"{request.node.name}.txt")


@dataclass(frozen=True)
class MyError(Error):
    title: ClassVar[str] = "Can't compare apples with oranges"
    span_label: ClassVar[str] = "Comparison attempted here"


def test_only_title(snapshot, request):
    @dataclass(frozen=True)
    class MyDiagnostic(Error):
        title: ClassVar[str] = "Can't compare apples with oranges"

    source = ""
    diagnostic = MyDiagnostic(None)
    run_test(source, diagnostic, snapshot, request)


def test_only_message(snapshot, request):
    @dataclass(frozen=True)
    class MyDiagnostic(Error):
        title: ClassVar[str] = "Can't compare apples with oranges"
        long_message: ClassVar[str] = (
            "Can't compare apples with oranges. Please refer to Barone (BMJ, 2000), "
            "https://doi.org/10.1136%2Fbmj.321.7276.1569 for further details."
        )

    source = ""
    diagnostic = MyDiagnostic(None)
    run_test(source, diagnostic, snapshot, request)


def test_only_label(snapshot, request):
    source = "apple == orange"
    span = Span(Loc(file, 1, 6), Loc(file, 1, 8))
    diagnostic = MyError(span)
    run_test(source, diagnostic, snapshot, request)


def test_message_with_span(snapshot, request):
    @dataclass(frozen=True)
    class MyDiagnostic(Error):
        title: ClassVar[str] = "Can't compare apples with oranges"
        long_message: ClassVar[str] = (
            "Please refer to Barone (BMJ, 2000), "
            "https://doi.org/10.1136%2Fbmj.321.7276.1569 for further details."
        )

    source = "apple == orange"
    span = Span(Loc(file, 1, 6), Loc(file, 1, 8))
    diagnostic = MyDiagnostic(span)
    run_test(source, diagnostic, snapshot, request)


def test_three_labels_formatted(snapshot, request):
    @dataclass(frozen=True)
    class MySubDiagnostic(Note):
        thing: str
        span_label: ClassVar[str] = "This is an {thing}"

    source = "apple == orange"
    span = Span(Loc(file, 1, 6), Loc(file, 1, 8))
    span_apple = Span(Loc(file, 1, 0), Loc(file, 1, 5))
    span_orange = Span(Loc(file, 1, 9), Loc(file, 1, 15))
    diagnostic = MyError(span)
    diagnostic.add_sub_diagnostic(MySubDiagnostic(span_apple, "apple"))
    diagnostic.add_sub_diagnostic(MySubDiagnostic(span_orange, "orange"))
    run_test(source, diagnostic, snapshot, request)


def test_long_label(snapshot, request):
    @dataclass(frozen=True)
    class MyDiagnostic(Error):
        title: ClassVar[str] = "Can't compare apples with oranges"
        span_label: ClassVar[str] = "Comparison attempted here. " * 20

    source = "apple == orange"
    span = Span(Loc(file, 1, 6), Loc(file, 1, 8))
    diagnostic = MyDiagnostic(span)
    run_test(source, diagnostic, snapshot, request)


def test_help(snapshot, request):
    @dataclass(frozen=True)
    class MySubDiagnostic(Help):
        message: ClassVar[str] = "Have you tried peeling the orange?"

    source = "apple == orange"
    span = Span(Loc(file, 1, 6), Loc(file, 1, 8))
    diagnostic = MyError(span)
    diagnostic.add_sub_diagnostic(MySubDiagnostic(None))
    run_test(source, diagnostic, snapshot, request)


def test_note(snapshot, request):
    @dataclass(frozen=True)
    class MySubDiagnostic(Note):
        message: ClassVar[str] = "Stop trying, this is a fruitless endeavor"

    source = "apple == orange"
    span = Span(Loc(file, 1, 6), Loc(file, 1, 8))
    diagnostic = MyError(span)
    diagnostic.add_sub_diagnostic(MySubDiagnostic(None))
    run_test(source, diagnostic, snapshot, request)


def test_context(snapshot, request):
    source = "super_apple := apple ** 2\nlemon := orange - apple\napple == orange"
    span = Span(Loc(file, 3, 6), Loc(file, 3, 8))
    diagnostic = MyError(span)
    run_test(source, diagnostic, snapshot, request)


def test_indented(snapshot, request):
    source = " " * 50 + "super_apple := apple ** 2\n"
    source += " " * 50 + "    lemon := orange - apple\n"
    source += " " * 50 + "        apple == orange"
    span = Span(Loc(file, 3, 50 + 8 + 6), Loc(file, 3, 50 + 8 + 8))
    diagnostic = MyError(span)
    run_test(source, diagnostic, snapshot, request)


def test_two_line_span(snapshot, request):
    source = "apple.compare(\n     orange) == EQUAL"
    span = Span(Loc(file, 1, 5), Loc(file, 2, 12))
    diagnostic = MyError(span)
    run_test(source, diagnostic, snapshot, request)


def test_three_line_span(snapshot, request):
    source = "apple.compare(\n     orange\n) == EQUAL"
    span = Span(Loc(file, 1, 5), Loc(file, 3, 1))
    diagnostic = MyError(span)
    run_test(source, diagnostic, snapshot, request)
