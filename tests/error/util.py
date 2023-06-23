import importlib.util
from typing import Callable, Optional, Any

import pytest

from guppy.compiler import GuppyModule
from guppy.hugr.hugr import Hugr


def guppy(f: Callable[..., Any]) -> Optional[Hugr]:
    """ Decorator to compile functions outside of modules for testing. """
    module = GuppyModule("module")
    module(f)
    return module.compile(exit_on_error=True)


def run_error_test(file, capsys):
    spec = importlib.util.spec_from_file_location("test_module", file)
    py_module = importlib.util.module_from_spec(spec)

    with pytest.raises(SystemExit):
        spec.loader.exec_module(py_module)

    err = capsys.readouterr().err

    with open(file.with_suffix(".err")) as f:
        exp_err = f.read()

    exp_err = exp_err.replace("$FILE", str(file))
    assert err == exp_err
