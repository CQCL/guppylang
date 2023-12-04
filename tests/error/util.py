import importlib.util
import pathlib
import pytest

from typing import Any
from collections.abc import Callable

from guppy.hugr import tys
from guppy.hugr.tys import TypeBound
from guppy.module import GuppyModule
from guppy.hugr.hugr import Hugr

import guppy.decorator as decorator


def guppy(f: Callable[..., Any]) -> Hugr | None:
    """ Decorator to compile functions outside of modules for testing. """
    module = GuppyModule("module")
    module.register_func_def(f)
    return module.compile()


def run_error_test(file, capsys):
    file = pathlib.Path(file)
    spec = importlib.util.spec_from_file_location("test_module", file)
    py_module = importlib.util.module_from_spec(spec)

    with pytest.raises(SystemExit):
        spec.loader.exec_module(py_module)

    err = capsys.readouterr().err

    with open(file.with_suffix(".err")) as f:
        exp_err = f.read()

    exp_err = exp_err.replace("$FILE", str(file))
    assert err == exp_err


util = GuppyModule("test")


@decorator.guppy.type(util, tys.Opaque(extension="", id="", args=[], bound=TypeBound.Copyable))
class NonBool:
    pass
