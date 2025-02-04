import importlib.util
import inspect
import pathlib
import sys

import pytest
from hugr import tys
from hugr.tys import TypeBound

from guppylang.module import GuppyModule

import guppylang.decorator as decorator


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

    snapshot.snapshot_dir = str(file.parent)
    snapshot.assert_match(err, file.with_suffix(".err").name)


util = GuppyModule("test")


@decorator.guppy.type(
    tys.Opaque(extension="", id="", args=[], bound=TypeBound.Copyable), module=util
)
class NonBool:
    pass
