import pytest
from pathlib import Path
from dataclasses import dataclass
from typing import ClassVar
from unittest.mock import Mock

from guppylang.diagnostic import MietteRenderer, DiagnosticsRenderer, Error, Note
from guppylang.span import SourceMap, Span, Loc, to_span


def test_miette_import():
    """Test that miette renderer can be imported and instantiated."""
    source_map = Mock(spec=SourceMap)
    
    try:
        import miette_py
    except ImportError as e:
        pytest.skip(f"miette-py not available: {e}")
    
    renderer = MietteRenderer(source_map)
    assert renderer is not None


def test_miette_module_functions():
    """Test that miette_py functions are available and functional."""
    try:
        from miette_py import guppy_to_miette, render_report
        
        # Test basic function call
        diag = guppy_to_miette(
            title="Test Error",
            level="error", 
            source_text="def foo(): pass",
            spans=[(4, 3, "function name")],
            message="This is a test",
            help_text=None
        )
        
        output = render_report(diag)
        assert isinstance(output, str)
        assert len(output) > 0
        
    except ImportError as e:
        pytest.skip(f"miette-py not available: {e}")


def test_basic_diagnostic_rendering(snapshot, request):
    """Test rendering of basic diagnostic with span highlighting."""
    try:
        import miette_py
    except ImportError:
        pytest.skip("miette-py not available")
    
    # Create real guppylang objects
    source_map = Mock(spec=SourceMap)
    source_map.span_lines = Mock(return_value=["def hello():", "    return x + 1"])
    
    file_path = "test.py"
    start_loc = Loc(file_path, 2, 11)  # position of 'x'
    end_loc = Loc(file_path, 2, 12)
    span = Span(start_loc, end_loc)
    
    @dataclass(frozen=True)
    class TestError(Error):
        title: ClassVar[str] = "Undefined variable 'x'"
        span_label: ClassVar[str] = "undefined variable"
        message: ClassVar[str] = "Variable 'x' is not defined in this scope"
        span: Span
    
    renderer = MietteRenderer(source_map)
    test_diag = TestError(span=span)
    renderer.render_diagnostic(test_diag)
    
    output = "\n".join(renderer.buffer)
    
    snapshot.snapshot_dir = str(Path(request.fspath).parent / "snapshots" / "miette")
    snapshot.assert_match(output, f"{request.node.name}.txt")


def test_multiple_spans_rendering(snapshot, request):
    """Test rendering with multiple span highlights."""
    try:
        import miette_py
    except ImportError:
        pytest.skip("miette-py not available")
    
    # Create real guppylang objects
    source_map = Mock(spec=SourceMap)
    source_map.span_lines = Mock(return_value=["def func(a, b):", "    return a + b + c + d"])
    
    file_path = "test.py"
    span_c = Span(Loc(file_path, 2, 19), Loc(file_path, 2, 20))  # position of 'c'
    span_d = Span(Loc(file_path, 2, 23), Loc(file_path, 2, 24))  # position of 'd'
    
    @dataclass(frozen=True)
    class TestError(Error):
        title: ClassVar[str] = "Multiple undefined variables"
        span_label: ClassVar[str] = "undefined 'c'"
        message: ClassVar[str] = "Multiple variables are not defined"
        span: Span
    
    @dataclass(frozen=True)
    class TestNote(Note):
        span_label: ClassVar[str] = "undefined 'd'"
        message: ClassVar[str] = None
        span: Span
    
    renderer = MietteRenderer(source_map)
    main_diag = TestError(span=span_c)
    sub_diag = TestNote(span=span_d)
    main_diag.add_sub_diagnostic(sub_diag)
    
    renderer.render_diagnostic(main_diag)
    output = "\n".join(renderer.buffer)
    
    snapshot.snapshot_dir = str(Path(request.fspath).parent / "snapshots" / "miette")
    snapshot.assert_match(output, f"{request.node.name}.txt")


def test_different_severity_levels():
    """Test diagnostic rendering across different severity levels."""
    try:
        from miette_py import guppy_to_miette, render_report
    except ImportError:
        pytest.skip("miette-py not available")
    
    source_code = "print('hello world')\n"
    
    # Test that different levels can be created and rendered without error
    for level in ["error", "warning", "note", "help"]:
        diag = guppy_to_miette(
            title=f"Test {level}",
            level=level,
            source_text=source_code,
            spans=[(0, 5, f"test {level} span")],
            message=f"This is a test {level}",
            help_text=None
        )
        
        output = render_report(diag)
        assert isinstance(output, str)
        assert len(output) > 0


def test_no_source_code_rendering(snapshot, request):
    """Test rendering diagnostics without source code."""
    try:
        import miette_py
    except ImportError:
        pytest.skip("miette-py not available")
    
    # Create a diagnostic without span (no source code)
    source_map = Mock(spec=SourceMap)
    
    @dataclass(frozen=True)
    class TestError(Error):
        title: ClassVar[str] = "Generic error"
        span_label: ClassVar[str] = None
        message: ClassVar[str] = "This is an error without source code"
        span: None = None
    
    renderer = MietteRenderer(source_map)
    test_diag = TestError()
    renderer.render_diagnostic(test_diag)
    
    output = "\n".join(renderer.buffer)
    
    snapshot.snapshot_dir = str(Path(request.fspath).parent / "snapshots" / "miette")
    snapshot.assert_match(output, f"{request.node.name}.txt")


def test_miette_renderer_integration():
    """Test MietteRenderer integration with real guppylang diagnostic objects."""
    try:
        import miette_py
    except ImportError:
        pytest.skip("miette-py not available")
    
    # Create real objects instead of complex mocks
    source_map = Mock(spec=SourceMap)
    source_map.span_lines = Mock(return_value=["def foo():", "    return x + 1"])
    
    file_path = "test.py"
    start_loc = Loc(file_path, 2, 11)
    end_loc = Loc(file_path, 2, 12)
    span = Span(start_loc, end_loc)
    
    @dataclass(frozen=True)
    class TestError(Error):
        title: ClassVar[str] = "Undefined variable"
        span_label: ClassVar[str] = "undefined variable"
        message: ClassVar[str] = "Variable 'x' is not defined"
        span: Span
    
    renderer = MietteRenderer(source_map)
    test_diag = TestError(span=span)
    
    # This should not raise an exception and should fill buffer
    renderer.render_diagnostic(test_diag)  # Returns None now
    assert len(renderer.buffer) > 0
    buffer_content = "\n".join(renderer.buffer)
    assert len(buffer_content) > 0


def test_edge_cases():
    """Test edge cases and error handling."""
    try:
        from miette_py import guppy_to_miette, render_report
    except ImportError:
        pytest.skip("miette-py not available")
    
    # Test empty title
    diag1 = guppy_to_miette("", "error", None, [], None, None)
    output1 = render_report(diag1)
    assert isinstance(output1, str)
    
    # Test overlapping spans
    diag2 = guppy_to_miette(
        "Overlapping spans",
        "error",
        "def func():\n    pass\n",
        [(0, 3, "keyword"), (4, 4, "function name"), (0, 8, "entire def")],
        None,
        None
    )
    output2 = render_report(diag2)
    assert isinstance(output2, str)
    assert len(output2) > 0
    
    # Test actual Unicode in source
    unicode_source = "def greet(name):\n    print(f'Hola {undefined} 🚀!')\n"
    diag3 = guppy_to_miette(
        "Unicode test",
        "error",
        unicode_source,
        [(32, 9, "undefined var")],
        "Unicode characters in source code",
        None
    )
    output3 = render_report(diag3)
    assert isinstance(output3, str)
    assert len(output3) > 0


def test_renderer_interface_consistency():
    """Test that MietteRenderer and DiagnosticsRenderer have consistent interfaces."""
    try:
        import miette_py
    except ImportError:
        pytest.skip("miette-py not available")
    
    source_map = Mock(spec=SourceMap)
    
    # Both renderers should be creatable
    standard_renderer = DiagnosticsRenderer(source_map)
    miette_renderer = MietteRenderer(source_map)
    
    # Both should have render_diagnostic method
    assert hasattr(standard_renderer, 'render_diagnostic')
    assert hasattr(miette_renderer, 'render_diagnostic')
    assert callable(standard_renderer.render_diagnostic)
    assert callable(miette_renderer.render_diagnostic)


def test_miette_with_sub_diagnostics():
    """Test miette rendering with sub-diagnostics (children)."""
    try:
        import miette_py
    except ImportError:
        pytest.skip("miette-py not available")
    
    source_map = Mock(spec=SourceMap)
    source_map.span_lines = Mock(return_value=["def calculate():", "    return a + b"])
    
    file_path = "test.py"
    main_span = Span(Loc(file_path, 2, 11), Loc(file_path, 2, 12))
    sub_span = Span(Loc(file_path, 2, 15), Loc(file_path, 2, 16))
    
    @dataclass(frozen=True)
    class TestError(Error):
        title: ClassVar[str] = "Multiple undefined variables"
        span_label: ClassVar[str] = "first undefined"
        message: ClassVar[str] = "Variables a and b are not defined"
        span: Span
    
    @dataclass(frozen=True)
    class TestNote(Note):
        span_label: ClassVar[str] = "second undefined"
        message: ClassVar[str] = "Variable b is also undefined"
        span: Span
    
    renderer = MietteRenderer(source_map)
    main_diag = TestError(span=main_span)
    sub_diag = TestNote(span=sub_span)
    main_diag.add_sub_diagnostic(sub_diag)
    
    # Should handle sub-diagnostics without error and fill buffer
    renderer.render_diagnostic(main_diag)  # Returns None now
    assert len(renderer.buffer) > 0
    buffer_content = "\n".join(renderer.buffer)
    assert len(buffer_content) > 0