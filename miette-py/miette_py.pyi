from typing import Optional, List, Tuple

class PyDiagnostic:
    def __init__(
        self,
        message: str,
        code: Optional[str],
        severity: str,
        source: Optional[str],
        spans: List[Tuple[int, int, Optional[str]]],
        help_text: Optional[str],
    ) -> None: ...

def render_report(diagnostic: PyDiagnostic) -> str: ...

def guppy_to_miette(
    title: str,
    level: str,
    source_text: Optional[str],
    spans: List[Tuple[int, int, Optional[str]]],
    message: Optional[str],
    help_text: Optional[str],
) -> PyDiagnostic: ...
