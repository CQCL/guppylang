import importlib.util
import pathlib
import pytest
import sys
from hugr import tys
from hugr.tys import TypeBound

from guppylang.error import GuppyError
from guppylang.module import GuppyModule

import guppylang.decorator as decorator


def run_error_test(file, capsys, snapshot):
    file = pathlib.Path(file)

    with pytest.raises(GuppyError) as exc_info:
        importlib.import_module(f"tests.error.{file.parent.name}.{file.name}")

    # Invoke except hook to print the exception to stderr
    sys.excepthook(exc_info.type, exc_info.value, exc_info.tb)

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
