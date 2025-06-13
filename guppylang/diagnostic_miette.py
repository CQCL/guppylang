from typing import Any

# Initially, this will try to import from the Rust module.
# You'll need to have built `miette-py` first (e.g., with `maturin develop`
# or `maturin build`).
try:
    # This assumes your `miette-py` wheel is installed in the environment
    # or `maturin develop` has placed the extension module where Python can find it.
    from miette_py import (  # type: ignore[import-untyped]
        render_miette_diagnostic_rust,  # Rust module
    )
except ImportError:
    # Fallback or error message if the Rust module is not built/found
    # Note: T201 `print` was here, removed for production code.
    # Consider logging instead if this warning is important for users.
    def render_miette_diagnostic_rust(diag_dict: dict[str, Any]) -> str:
        return (
            f"Fallback renderer: Rust miette_py module not loaded. "
            f"Diagnostic: {diag_dict.get('message', 'Unknown error')}"
        )


def convert_guppy_diagnostic_to_dict(
    guppy_diag: Any, source_map: Any | None = None
) -> dict[str, Any]:
    """
    Converts a Guppy Diagnostic object to a dictionary format
    suitable for passing to the miette Rust bindings.
    """
    diag_dict: dict[str, Any] = {
        "message": (
            getattr(guppy_diag, "rendered_title", None)
            or getattr(guppy_diag, "message", str(guppy_diag))
        ),
        "code": getattr(guppy_diag, "code", None),
        "help_text": getattr(guppy_diag, "help_text", None),
        "severity_str": getattr(
            getattr(guppy_diag, "level", None), "name", "ERROR"
        ).upper(),
    }

    labels_data: list[dict[str, Any]] = []
    current_source_set = False

    # Handle primary span and label for the current diagnostic
    if hasattr(guppy_diag, "span") and guppy_diag.span and source_map:
        span = guppy_diag.span
        if hasattr(span.file, "name"):
            diag_dict["source_name"] = str(span.file.name)
            source_text = source_map.get_file_content_by_id(str(span.file.name))
            if source_text is not None:
                diag_dict["source_text"] = source_text
                current_source_set = True
            label_text = getattr(guppy_diag, "label_text", None)
            if label_text and current_source_set:
                labels_data.append(
                    {
                        "text": label_text,
                        "offset": span.start.offset,
                        "length": len(span),
                    }
                )

    # Handle additional labels for the current diagnostic
    if hasattr(guppy_diag, "additional_labels") and source_map:
        for add_span, add_label_text in guppy_diag.additional_labels:
            if add_span and add_label_text and hasattr(add_span.file, "name"):
                if (
                    not current_source_set
                ):  # Set source if not already set by primary span
                    diag_dict["source_name"] = str(add_span.file.name)
                    source_text = source_map.get_file_content_by_id(
                        str(add_span.file.name)
                    )
                    if source_text is not None:
                        diag_dict["source_text"] = source_text
                        current_source_set = True
                if current_source_set:
                    labels_data.append(
                        {
                            "text": add_label_text,
                            "offset": add_span.start.offset,
                            "length": len(add_span),
                        }
                    )
    if labels_data:
        diag_dict["labels_data"] = labels_data
    # Recursively convert children
    if hasattr(guppy_diag, "children") and guppy_diag.children:
        diag_dict["children"] = [
            convert_guppy_diagnostic_to_dict(child, source_map)  # Pass source_map
            for child in guppy_diag.children
        ]

    return {k: v for k, v in diag_dict.items() if v is not None}


def render_diagnostic_with_miette(
    guppy_diag: Any,
    source_map: Any | None = None,
    use_colors: bool = True,
    footer: str | None = None,
    context_lines: int | None = None,
) -> str:
    """
    Renders a Guppy diagnostic object using the miette Rust bindings.

    `source_map` would be Guppy's SourceMap for providing source code snippets.
    `use_colors` controls whether ANSI color codes are used in the output.
    `footer` an optional string to append at the end of the report.
    `context_lines` sets the number of source code lines to display before and
    after the error.
    """
    diag_dict = convert_guppy_diagnostic_to_dict(guppy_diag, source_map)
    diag_dict["use_colors_param"] = use_colors
    if footer is not None:
        diag_dict["footer_param"] = footer
    if context_lines is not None:
        diag_dict["context_lines_param"] = context_lines

    # The imported render_miette_diagnostic_rust is from an untyped native module.
    # mypy infers its return as Any. We ignore the potential Any return here.
    return render_miette_diagnostic_rust(diag_dict)  # type: ignore[no-any-return]
