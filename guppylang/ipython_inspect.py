"""Tools for inspecting source code when running in IPython."""

import ast
from typing import Any, NamedTuple, cast


def is_running_ipython() -> bool:
    """Checks if we are currently running in IPython"""
    try:
        return get_ipython() is not None  # type: ignore[name-defined]
    except NameError:
        return False


def is_ipython_dummy_file(filename: str) -> bool:
    """Checks whether a given filename is a dummy name generated for an IPython cell."""
    # TODO: The approach below is false-positive prone. Figure out if there is a better
    #  way to do this.
    return (
        # IPython cells have filenames like "<ipython-input-3-3e9b5833de21>"
        filename.startswith("<ipython-input-")
        # Jupyter cells have filenames like "/var/{...}/ipykernel_82076/61218616.py"
        or "ipykernel_" in filename
    )


def get_ipython_cell_sources() -> list[str]:
    """Returns the source code of all cells in the running IPython session.

    See https://github.com/wandb/weave/pull/1864
    """
    shell = get_ipython()  # type: ignore[name-defined]  # noqa: F821
    if not hasattr(shell, "user_ns"):
        raise AttributeError("Cannot access user namespace")
    cells = cast(list[str], shell.user_ns["In"])
    # First cell is always empty
    return cells[1:]


class IPythonDef(NamedTuple):
    """AST of a definition in IPython together with the definition cell name."""

    node: ast.FunctionDef | ast.ClassDef
    cell_name: str
    cell_source: str


def find_ipython_def(name: str) -> IPythonDef | None:
    """Tries to find a definition matching a given name in the current IPython session.

    Note that this only finds *top-level* function or class definitions. Nested
    definitions are not detected.

    See https://github.com/wandb/weave/pull/1864
    """
    cell_sources = get_ipython_cell_sources()
    # Search cells in reverse order to find the most recent version of the definition
    for i, cell_source in enumerate(reversed(cell_sources)):
        try:
            cell_ast = ast.parse(cell_source)
        except SyntaxError:
            continue
        # Search body in reverse order to find the most recent version of the class
        for node in reversed(cell_ast.body):
            if isinstance(node, ast.FunctionDef | ast.ClassDef) and node.name == name:
                cell_name = f"In [{len(cell_sources) - i}]"
                return IPythonDef(node, cell_name, cell_source)
    return None


def get_ipython_globals() -> dict[str, Any]:
    """Returns the globals of the current IPython kernel."""
    try:
        return get_ipython().user_ns  # type: ignore[name-defined, no-any-return]
    except NameError:
        raise RuntimeError("Not running in IPython") from None
