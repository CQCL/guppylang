import importlib.util
import pathlib
import pytest

from typing import Any
from collections.abc import Callable

from guppy.hugr import tys
from guppy.hugr.tys import TypeBound
from guppy.module import GuppyModule

import guppy.decorator as decorator


def run_error_test(file, capsys):
    file = pathlib.Path(file)
    spec = importlib.util.spec_from_file_location("test_module", file)
    py_module = importlib.util.module_from_spec(spec)

    with pytest.raises(SystemExit):
        spec.loader.exec_module(py_module)

    err = capsys.readouterr().err

    with pathlib.Path(file.with_suffix(".err")).open() as f:
        exp_err = f.read()

    exp_err = exp_err.replace("$FILE", str(file))
    assert err == exp_err


util = GuppyModule("test")


@decorator.guppy.type(
    util, tys.Opaque(extension="", id="", args=[], bound=TypeBound.Copyable)
)
class NonBool:
    pass
