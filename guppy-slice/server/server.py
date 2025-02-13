import logging
import sys
import os

from dataclasses import dataclass
from pygls.server import LanguageServer
from lsprotocol.types import Diagnostic, DiagnosticSeverity, DiagnosticTag, Position, Range, PublishDiagnosticsParams

from guppylang.checker.core import Variable

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dependency_analyser import ProgramDependencies
import source_analyser


@dataclass
class ServerState:
    # TODO: Better interface for this.
    # Stores a map from URI to a map from function name to dependencies.
    deps: dict[str, dict[str, tuple[ProgramDependencies, int]]]

    def __init__(self):
        self.deps = {}


server_state = ServerState()
server = LanguageServer("guppySliceServer", "v0.1")


@server.command("computeDependencies")
def compute_deps(ls: LanguageServer, params):
    uri = params[0]["uri"]
    # ls.show_message(f"Processing: {uri}")
    try:
        deps = source_analyser.compute_dependencies(uri)
        server_state.deps[uri] = deps
        return True
    except Exception as e:
        ls.show_message(f"Error computing dependencies: {e}")
        return False


@server.command("computeSlice")
def compute_slice(ls: LanguageServer, params):
    uri = params[0]["uri"]
    word = params[0]["word"]
    position = Position(line=params[0]["position"]["line"], character=params[0]["position"]["character"])


    # TODO: Be more consistent with the way we handle file paths.
    file_path = source_analyser.get_file_path(uri)

    # Retrieve previously computed dependencies.
    uri_deps = server_state.deps.get(uri)
    if len(uri_deps) == 0:
        ls.show_message(f"Dependencies not computed for {uri}")
        return

    # Find relevant function based on selection position.
    func = source_analyser.get_function_name_at_position(file_path, position)
    if func == "":
        ls.show_message(f"No function found at position {position}")
        return

    # Retrieve dependencies for the function.
    func_deps = uri_deps.get(func)
    var = Variable.Id(word)  # Assumption: selection is a variable.
    slice_spans = source_analyser.get_dep_spans_for_var(var, func_deps)

    if slice_spans == []:
        ls.show_message(f"No dependencies found for {var} in {func}")
        return

    # Send the inverse of the computed slice to the client.
    inverse_spans = source_analyser.compute_inverse_spans(file_path, slice_spans)
    diagnostics_list = []
    for span in inverse_spans:
        diagnostics_list.append(Diagnostic(
                range=Range(
                    start=Position(line=span[0].line, character=span[0].character),
                    end=Position(line=span[1].line, character=span[1].character),
                ),
                message="Not relevant to the selected variable",
                severity=DiagnosticSeverity.Hint,
                tags=[DiagnosticTag.Unnecessary],
        ))
    ls.publish_diagnostics(str(uri), diagnostics=diagnostics_list)


@server.command("clearDiagnostics")
def clear_diagnostics(ls: LanguageServer, params: list):
    uri = params[0].get("uri")
    
    # Clear diagnostics by publishing an empty list
    ls.publish_diagnostics(str(uri), diagnostics=[])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    server.start_io()
