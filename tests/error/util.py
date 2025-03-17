import importlib.util
import inspect
import pathlib
import re
import sys

import pytest
import sys
from hugr import tys
from hugr.tys import TypeBound

from guppylang.module import GuppyModule

import guppylang.decorator as decorator


# Regular expression to match the `~~~~~^^^~~~` highlights that are printed in
# tracebacks from Python 3.11 onwards. We strip those out so we can use the same golden
# files for Python 3.10
TRACEBACK_HIGHLIGHT = re.compile(r" *~*\^\^*~*")


def run_error_test(file, capsys, snapshot):
    file = pathlib.Path(file)

    with pytest.raises(Exception) as exc_info:
        importlib.import_module(f"tests.error.{file.parent.name}.{file.name}")

    # Remove the importlib frames from the traceback by skipping beginning frames until
    # we end up in the executed file
    tb = exc_info.tb
    while tb is not None and inspect.getfile(tb.tb_frame) != str(file):
        tb = tb.tb_next

    # Invoke except hook to print the exception to stderr
    sys.excepthook(exc_info.type, exc_info.value.with_traceback(tb), tb)

    err = capsys.readouterr().err
    err = err.replace(str(file), "$FILE")

    # If we're comparing tracebacks, strip the highlights that are only present for
    # Python 3.11+
    if err.startswith("Traceback (most recent call last):"):
        err = "\n".join(
            line
            for line in err.split("\n")
            if not TRACEBACK_HIGHLIGHT.fullmatch(line)
        )

    snapshot.snapshot_dir = str(file.parent)
    snapshot.assert_match(err, file.with_suffix(".err").name)


util = GuppyModule("test")


@decorator.guppy.type(
    tys.Opaque(extension="", id="", args=[], bound=TypeBound.Copyable), module=util
)
class NonBool:
    pass
