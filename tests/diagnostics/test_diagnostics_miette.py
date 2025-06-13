import re  # For checking ANSI codes
from typing import Any  # Import necessary typing modules at the top

import pytest

from guppylang.diagnostic_miette import render_diagnostic_with_miette

# For direct rust call test, import directly from the extension module
# This makes its origin clearer for type checking.
try:
    from miette_py import (  # type: ignore[import-untyped]
        render_miette_diagnostic_rust as rust_render_direct_typed,
    )  # This line (closing parenthesis) should be clean of any type: ignore comments
except ImportError:
    # Define a fallback if the rust module is not available,
    # to satisfy mypy during tests
    def rust_render_direct_typed(diag_dict: dict[str, Any]) -> str:
        return "Rust module not available"


# Mock Span and related objects for testing - Add type hints
class MockLoc:
    def __init__(self, offset: int):
        self.offset = offset


class MockFileId:
    def __init__(self, name: str):
        self.name = name


class MockSpan:
    def __init__(self, file_id: MockFileId, start_offset: int, end_offset: int):
        self.file = file_id
        self.start = MockLoc(start_offset)
        self.end = MockLoc(end_offset)

    def __len__(self) -> int:
        return self.end.offset - self.start.offset


# A simple dummy diagnostic class for initial testing - Add type hints
class DummyGuppyDiagnostic:
    def __init__(
        self,
        title: str,
        message: str | None = None,
        code: str | None = None,
        span: MockSpan | None = None,
        # Use string literal for forward reference
        children: list["DummyGuppyDiagnostic"]
        | None = None,  # UP037 applied by ruff --fix
        level_name: str = "ERROR",
        label_text: str | None = None,
        help_text: str | None = None,
        additional_labels: list[tuple[MockSpan, str]] | None = None,
    ):
        self.rendered_title = title
        self.message = message
        self.code = code
        self.span = span  # Primary span
        self.children: list[DummyGuppyDiagnostic] = children or []  # Fix UP037
        self._level_name = level_name
        self.label_text = label_text  # Text for primary span
        self.help_text = help_text
        # List of (MockSpan, str_label_text)
        self.additional_labels: list[tuple[MockSpan, str]] = additional_labels or []

    @property
    def level(self) -> Any:  # Keep Any for MockLevel for simplicity in this context
        # Mock the level object Guppy's Diagnostic might have
        class MockLevel:
            def __init__(self, name: str):
                self.name = name

        return MockLevel(self._level_name)

    def __str__(self) -> str:
        return self.rendered_title


# Mock SourceMap for testing purposes - Add type hints
class MockSourceMap:
    def __init__(self) -> None:
        self.files: dict[str, str] = {}  # file_id_str: content

    def add_file(self, file_id_str: str, content: str) -> None:
        self.files[file_id_str] = content

    def get_file_content_by_id(self, file_id_str: str) -> str | None:
        return self.files.get(file_id_str)


def test_direct_rust_call_simple_message() -> None:
    """Tests calling the Rust function directly with a simple message."""
    # Ensure the Rust module is importable, otherwise skip
    try:
        # We already imported rust_render_direct_typed at the top
        _ = rust_render_direct_typed  # Check if it's defined
    except NameError:  # Fallback if the import failed at the top
        pytest.skip("Rust miette_py module not available for direct call test.")

    diag_dict: dict[str, Any] = {"message": "A direct test error from Rust"}
    # When called directly, use_colors_param defaults to True in Rust if not provided
    output = rust_render_direct_typed(diag_dict)
    # print(f"Direct Rust output:\n{output}") # T201 removed
    assert "A direct test error from Rust" in output
    # Miette unicode theme uses '×' (multiplication sign) for error # noqa: RUF003
    # Check for unicode error marker, with or without color for flexibility
    assert "  \x1b[31m×\x1b[0m " in output or "  × " in output  # noqa: RUF001


def test_render_simple_diagnostic_with_miette_wrapper() -> None:
    """Tests rendering a very simple diagnostic message via the Python wrapper."""
    diag = DummyGuppyDiagnostic(title="A simple test error via wrapper")
    output = render_diagnostic_with_miette(diag)  # use_colors=True by default

    # print(f"Miette output (wrapper):\n{output}") # T201 removed
    assert "A simple test error via wrapper" in output
    # Miette unicode theme uses '×' # noqa: RUF003
    assert "  \x1b[31m×\x1b[0m " in output or "  × " in output  # noqa: RUF001


def test_render_diagnostic_with_code_via_wrapper() -> None:
    """Tests rendering a diagnostic that includes an error code via the wrapper."""
    diag = DummyGuppyDiagnostic(title="An error with a code", code="E001")
    output = render_diagnostic_with_miette(diag)

    # print(f"Miette output (with code via wrapper):\n{output}") # T201 removed
    assert "An error with a code" in output
    # Check for the dynamic code "E001"
    assert "E001" in output


def test_render_diagnostic_without_code_via_wrapper() -> None:
    """Tests rendering a diagnostic where no code is provided."""
    diag = DummyGuppyDiagnostic(title="An error without a code")  # No code provided
    output = render_diagnostic_with_miette(diag)

    # print(f"Miette output (without code via wrapper):\n{output}") # T201 removed
    assert "An error without a code" in output
    # Assert that common code renderings (like parentheses) are not present
    # if the code string was empty. Miette might just omit the code part.
    # We also want to ensure our previous placeholder "LITERAL_CODE_TEST" is not there.
    assert "()" not in output
    assert "[]" not in output
    assert "LITERAL_CODE_TEST" not in output
    # A more robust check might be to ensure the line with the error message
    # does not contain typical code delimiters if the code was empty.
    # For now, checking for absence of common patterns is a good start.


def test_render_diagnostic_with_source_and_label() -> None:
    """Tests rendering a diagnostic with source code and a primary label."""
    source_content = "def foo():\n    x = 1 + bar\n    return x"
    file_id_str = "test_file.py"
    source_map = MockSourceMap()
    source_map.add_file(file_id_str, source_content)
    file_id = MockFileId(file_id_str)
    # Span for "bar" in "x = 1 + bar"
    # "def foo():\n" is 11 chars
    # "    x = 1 + " is 12 chars
    # "bar" starts at offset 11 + 12 = 23, length 3
    span = MockSpan(file_id, start_offset=23, end_offset=26)
    diag = DummyGuppyDiagnostic(
        title="Name not found",
        code="E002",
        span=span,
        label_text="Unknown name 'bar'",
    )
    output = render_diagnostic_with_miette(
        diag, source_map
    )  # use_colors=True by default
    # print(f"Miette output (with source and label):\n{output}") # T201 removed
    assert "Name not found" in output
    assert "E002" in output
    assert "test_file.py" in output  # Check for filename
    assert "x = 1 + bar" in output  # Check for relevant source line
    assert "Unknown name 'bar'" in output  # Check for label text
    # Miette unicode theme uses box-drawing characters for spans
    assert "─┬─" in output  # Part of the unicode span drawing for a 3-char span
    assert "╰──" in output  # Part of the unicode span drawing


def test_render_diagnostic_with_help_message() -> None:
    """Tests rendering a diagnostic that includes a help message."""
    help_message = "Consider defining 'bar' or check for typos."
    diag = DummyGuppyDiagnostic(
        title="Name not found", code="E002", help_text=help_message
    )
    output = render_diagnostic_with_miette(diag)  # No source_map needed for this test
    # print(f"Miette output (with help message):\n{output}") # T201 removed
    assert "Name not found" in output
    assert "E002" in output
    # Miette typically prefixes help messages with "help:" or similar,
    # or renders them in a distinct section.
    # The exact formatting can vary, so we check for the presence of the help text.
    assert help_message in output
    # A common rendering pattern for help is "╰─▶" or "help:"
    # We can check for one of these or just the text for now.
    # Let's be a bit more specific if possible, e.g. miette often uses "💡" or "help:"
    # For now, just checking the text is safest until we observe the exact output.
    # After observing, we might refine this to: assert f"💡 {help_message}" in output
    # or assert f"help: {help_message}" in output


def test_render_diagnostic_with_multiple_labels() -> None:
    """Tests rendering a diagnostic with multiple labels on the same source."""
    source_content = "let a = 10;\nlet b = a + c;"
    file_id_str = "multi_label.guppy"

    source_map = MockSourceMap()
    source_map.add_file(file_id_str, source_content)
    file_id = MockFileId(file_id_str)

    # Span for 'a' in "a + c" (second line)
    # "let a = 10;\n" (12 chars)
    # "let b = " (8 chars)
    # 'a' is at offset 12 + 8 = 20, length 1
    span1 = MockSpan(file_id, start_offset=20, end_offset=21)
    label1_text = "first occurence of 'a'"
    # Span for 'c' in "a + c"
    # "a + " (4 chars after start of span1)
    # 'c' is at offset 20 + 4 = 24, length 1
    span2 = MockSpan(file_id, start_offset=24, end_offset=25)
    label2_text = "undeclared variable 'c'"

    diag = DummyGuppyDiagnostic(
        title="Type checking error",
        code="E003",
        # Primary span and label (optional, could be one of the additional_labels too)
        # For this test, let's make the first label the "primary" one via
        # span/label_text and the second one via additional_labels.
        span=span1,
        label_text=label1_text,
        additional_labels=[(span2, label2_text)],
        help_text="Ensure all variables are declared.",
    )

    output = render_diagnostic_with_miette(diag, source_map)
    # print(f"Miette output (with multiple labels):\n{output}") # T201 removed
    assert "Type checking error" in output
    assert "E003" in output
    assert file_id_str in output
    assert "let b = a + c;" in output  # Check for relevant source line
    assert label1_text in output
    assert label2_text in output
    assert "Ensure all variables are declared." in output
    # Check for miette's rendering of multiple labels.
    # For single-character spans on the same line, miette uses '|'.


def test_render_diagnostic_with_warning_severity() -> None:
    """Tests rendering a diagnostic with WARNING severity."""
    diag = DummyGuppyDiagnostic(
        title="Possible unused variable",
        code="W001",
        level_name="WARNING",  # Set severity to WARNING
        help_text="Consider removing 'y' if it's not used.",
    )
    output = render_diagnostic_with_miette(diag)  # use_colors=True by default
    # print(f"Miette output (Warning severity):\n{output}") # T201 removed
    assert "Possible unused variable" in output
    assert "W001" in output
    assert "Consider removing 'y' if it's not used." in output
    # Miette unicode theme uses '⚠' for warnings
    assert "  \x1b[33m⚠\x1b[0m " in output or "  ⚠ " in output


def test_render_diagnostic_with_advice_severity() -> None:
    """Tests rendering a diagnostic with ADVICE severity."""
    diag = DummyGuppyDiagnostic(
        title="Style suggestion",
        code="A001",
        level_name="ADVICE",  # Set severity to ADVICE
        help_text="Consider using more descriptive variable names.",
    )
    output = render_diagnostic_with_miette(diag)  # use_colors=True by default
    # print(f"Miette output (Advice severity):\n{output}") # T201 removed
    assert "Style suggestion" in output
    assert "A001" in output
    assert "Consider using more descriptive variable names." in output
    # Miette unicode theme uses '☞' for advice
    assert "  \x1b[36m☞\x1b[0m " in output or "  ☞ " in output


def test_render_diagnostic_with_children() -> None:
    """Tests rendering a diagnostic with sub-diagnostics (children)."""
    source_content = "def main():\n    a = unknown_var + 10\n    b = another_unknown"
    file_id_str = "children_test.py"

    source_map = MockSourceMap()
    source_map.add_file(file_id_str, source_content)
    file_id = MockFileId(file_id_str)

    # Span for 'unknown_var'
    span_child1 = MockSpan(file_id, start_offset=16, end_offset=27)  # "unknown_var"
    child1_label = "This variable is not defined"
    child1 = DummyGuppyDiagnostic(
        title="Undefined variable 'unknown_var'",
        code="E002",
        span=span_child1,
        label_text=child1_label,
        level_name="ERROR",  # Child is an error
    )

    # Span for 'another_unknown'
    span_child2 = MockSpan(file_id, start_offset=40, end_offset=55)  # "another_unknown"
    child2_label = "This one is also not defined"
    child2 = DummyGuppyDiagnostic(
        title="Undefined variable 'another_unknown'",
        code="E002",
        span=span_child2,
        label_text=child2_label,
        level_name="ERROR",  # Child is an error
    )
    # A note-like child without a span
    # Using title as note

    child3_note = DummyGuppyDiagnostic(
        title="Consider checking your variable declarations.",
        level_name="ADVICE",  # Or could be a specific "NOTE" level if we add it
    )

    parent_diag = DummyGuppyDiagnostic(
        title="Multiple issues found in 'main'",
        code="E000",
        # No primary span/label for parent, its details come from children
        children=[child1, child2, child3_note],
        help_text="Please fix the errors listed above.",
    )

    output = render_diagnostic_with_miette(parent_diag, source_map)
    # print(f"Miette output (with children):\n{output}") # T201 removed
    assert "Multiple issues found in 'main'" in output  # Parent title
    assert "E000" in output  # Parent code
    assert "Please fix the errors listed above." in output  # Parent help

    # Check for child1 details
    assert "Undefined variable 'unknown_var'" in output
    assert child1_label in output
    assert "a = unknown_var + 10" in output  # Source line for child1

    # Check for child2 details
    assert "Undefined variable 'another_unknown'" in output
    assert child2_label in output
    assert "b = another_unknown" in output  # Source line for child2
    # Check for child3_note (note-like child)
    assert "Consider checking your variable declarations." in output
    # Check for ADVICE prefix for the note
    # For unicode theme, this will be the '☞' symbol
    assert (
        "  \x1b[36m☞\x1b[0m Consider checking your variable declarations." in output
        or "  ☞ Consider checking your variable declarations." in output
    )

    # Check that miette indicates related diagnostics (often with a bullet or numbering)
    # For unicode theme, error children will have the '×' prefix. # noqa: RUF003
    assert output.count("  \x1b[31m×\x1b[0m ") >= 2 or output.count("  × ") >= 2  # noqa: RUF001


def test_render_diagnostic_without_colors() -> None:
    """Tests rendering a diagnostic with colors disabled (uses ascii theme)."""
    diag = DummyGuppyDiagnostic(
        title="An error message", code="E999", level_name="ERROR"
    )
    output_with_colors = render_diagnostic_with_miette(diag, use_colors=True)
    output_without_colors = render_diagnostic_with_miette(diag, use_colors=False)

    # print( # T201 removed
    #     "Miette output (with colors by default - unicode theme):\n"
    #     f"{output_with_colors}"
    # )
    # print( # T201 removed
    #     "Miette output (colors disabled - ascii theme):\n"
    #     f"{output_without_colors}"
    # )

    # ANSI escape codes typically start with \x1b[
    ansi_escape_pattern = re.compile(r"\x1b\[[0-9;]*m")

    assert ansi_escape_pattern.search(output_with_colors), (
        "Expected ANSI color codes in unicode theme output"
    )
    # With ascii theme, miette 7.6.0 still colors the diagnostic code and
    # severity marker.
    # The main message text should be uncolored.
    # We will check for ASCII characters for markers.
    assert "E999" in output_without_colors  # Code should be present
    assert "An error message" in output_without_colors  # Message should be present
    # ASCII 'x' for error marker, which is colored red by miette's ascii theme
    assert "  \x1b[31mx\x1b[0m " in output_without_colors

    # Verify that the main message part is not colored in the ascii output
    # A simpler check: ensure unicode specific markers are NOT in ascii output
    # Unicode multiplication sign
    assert "×" not in output_without_colors  # noqa: RUF001
    assert "⚠" not in output_without_colors  # Unicode warning sign
    assert "☞" not in output_without_colors  # Unicode pointing finger

    # Check if the error code and marker are colored (as observed)
    # output_without_colors.splitlines()[0] is like "\x1b[31mE999\x1b[0m"
    # output_without_colors.splitlines()[2] is like
    # "  \x1b[31mx\x1b[0m An error message"
    assert ansi_escape_pattern.search(output_without_colors.splitlines()[0]), (
        "ASCII theme should color the code line"
    )
    assert ansi_escape_pattern.search(output_without_colors.splitlines()[2]), (
        "ASCII theme should color the marker line"
    )
    # Check that the message "An error message" itself is not colored
    message_line_ascii = ""
    for line in output_without_colors.splitlines():
        if "An error message" in line:
            message_line_ascii = line
            break
    assert "An error message" in message_line_ascii
    # Isolate the message part after the colored marker
    # The marker is "  \x1b[31mx\x1b[0m "
    if "  \x1b[31mx\x1b[0m " in message_line_ascii:
        message_text_part = message_line_ascii.split("  \x1b[31mx\x1b[0m ", 1)[1]
        assert not ansi_escape_pattern.search(message_text_part), (
            f"Message text '{message_text_part}' should not be colored in ascii theme"
        )
    else:
        # Fallback if the exact colored marker isn't found as expected,
        # though the previous assertion should catch this.
        # This part of the test might need adjustment if the marker format changes.
        pass


def test_render_diagnostic_with_footer() -> None:
    """Tests rendering a diagnostic with a custom footer."""
    diag = DummyGuppyDiagnostic(title="An error with a footer", code="F001")
    footer_text = "This is a custom footer."
    output = render_diagnostic_with_miette(diag, footer=footer_text)

    # print(f"Miette output (with footer):\n{output}") # T201 removed
    assert "An error with a footer" in output
    assert "F001" in output
    assert footer_text in output
    # Check that the footer appears after the main diagnostic message
    # A simple check is that the footer is one of the last things in the output.
    assert output.strip().endswith(footer_text.strip())


def strip_ansi_codes(s: str) -> str:
    """Removes ANSI escape codes from a string."""
    return re.sub(r"\x1b\[[0-9;]*m", "", s)


def test_render_diagnostic_with_context_lines() -> None:
    """Tests rendering a diagnostic with custom number of context lines."""
    source_content = (
        "line 1\n"
        "line 2\n"
        "line 3 (before error)\n"
        "line 4 (error here)\n"  # Error on this line
        "line 5 (after error)\n"
        "line 6\n"
        "line 7"
    )
    file_id_str = "context_lines_test.py"
    source_map = MockSourceMap()
    source_map.add_file(file_id_str, source_content)
    file_id = MockFileId(file_id_str)
    error_line_offset = source_content.find("line 4 (error here)")
    span_offset = error_line_offset + source_content[error_line_offset:].find(
        "error here"
    )
    span_length = len("error here")
    span = MockSpan(
        file_id, start_offset=span_offset, end_offset=span_offset + span_length
    )

    diag = DummyGuppyDiagnostic(
        title="Context lines test",
        code="C001",
        span=span,
        label_text="This is the error",
    )

    # Render with 1 context line
    output_1_context = render_diagnostic_with_miette(diag, source_map, context_lines=1)
    # print(f"Miette output (1 context line):\n{output_1_context}") # T201 removed

    # Render with 0 context lines
    output_0_context = render_diagnostic_with_miette(diag, source_map, context_lines=0)
    # print(f"Miette output (0 context lines):\n{output_0_context}") # T201 removed

    # Check output with 1 context line
    assert "line 3 (before error)" in output_1_context
    assert "line 4 (error here)" in output_1_context
    assert "line 5 (after error)" in output_1_context
    assert "line 1" not in output_1_context
    assert "line 2" not in output_1_context
    assert "line 6" not in output_1_context
    assert "line 7" not in output_1_context
    # Count visible source lines in the output for 1 context line
    # Expected: 1 before + 1 error line + 1 after = 3 lines
    source_lines_in_output_1 = [
        line
        for line in output_1_context.splitlines()
        # Strip ANSI and check for "N |" pattern
        if re.search(r"^\s*\d+\s*│", strip_ansi_codes(line))
    ]
    assert len(source_lines_in_output_1) == 3, (
        f"Expected 3 source lines for 1 context line, "
        f"got {len(source_lines_in_output_1)}.\nOutput:\n{output_1_context}"
    )

    # Check output with 0 context lines
    # For context_lines=0, miette shows only the spanned part of the line
    # if the span is smaller than the line.
    assert "error here" in output_0_context  # Check for the spanned text
    # Ensure the text before the span on that line is not present
    assert "line 4 (" not in output_0_context
    # Ensure the text after the span on that line is not present,
    # checking the specific line after stripping ANSI
    assert ")" not in strip_ansi_codes(output_0_context).splitlines()[4]
    assert "line 3 (before error)" not in output_0_context
    assert "line 5 (after error)" not in output_0_context

    source_lines_in_output_0 = [
        line
        for line in output_0_context.splitlines()
        # Strip ANSI and check for "N |" pattern
        if re.search(r"^\s*\d+\s*│", strip_ansi_codes(line))
    ]
    assert len(source_lines_in_output_0) == 1, (
        f"Expected 1 source line for 0 context lines, "
        f"got {len(source_lines_in_output_0)}.\nOutput:\n{output_0_context}"
    )


# To run these tests:
# pytest -v --tb=short --disable-warnings > test_results.txt
# Check test_results.txt for detailed output, especially for rendered diagnostics.
