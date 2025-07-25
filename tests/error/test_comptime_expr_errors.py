from importlib.util import find_spec

import pathlib
import pytest

from tests.error.util import run_error_test


tket_installed = find_spec("tket") is not None


path = pathlib.Path(__file__).parent.resolve() / "comptime_expr_errors"
files = [
    x
    for x in path.iterdir()
    if x.is_file()
    and x.suffix == ".py"
    and x.name not in ("__init__.py", "tket_not_installed.py")
]

# Turn paths into strings, otherwise pytest doesn't display the names
files = [str(f) for f in files]


@pytest.mark.parametrize("file", files)
@pytest.mark.skipif(not tket_installed, reason="tket is not installed")
def test_comptime_expr_errors(file, capsys, snapshot):
    run_error_test(file, capsys, snapshot)


@pytest.mark.skipif(tket_installed, reason="tket is installed")
def test_tket_not_installed(capsys, snapshot):
    path = (
        pathlib.Path(__file__).parent.resolve() / "py_errors" / "tket_not_installed.py"
    )
    run_error_test(str(path), capsys, snapshot)
