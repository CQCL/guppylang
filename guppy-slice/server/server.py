from dataclasses import dataclass
import logging

from pygls.server import LanguageServer
from lsprotocol import types

server = LanguageServer("guppySliceServer", "v0.1")


@dataclass
class ServerState:
    focus_mode: bool


def toggle(self):
    self.focus_mode = not self.focus_mode
    logging.debug("Toggled focus mode")
    if self.focus_mode:
        # (Re-)run analysis to populate dependencies.
        pass


def focus_mode_status(self) -> str:
    if self.focus_mode:
        return "on"
    else:
        return "off"


server_state = ServerState(False)


@server.command("toggleFocusMode")
def toggle_variable(ls: LanguageServer, *args):
    global server_state
    server_state.toggle()
    ls.show_message(f"Focus mode is now {server_state.focus_mode_status}")


@server.feature(types.TEXT_DOCUMENT_DID_OPEN)
@server.feature(types.TEXT_DOCUMENT_DID_CHANGE)
def did_open_or_change(ls: LanguageServer, params: types.DidOpenTextDocumentParams):
    pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    server.start_io()
