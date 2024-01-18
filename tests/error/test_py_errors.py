import pathlib
import pytest

from tests.error.util import run_error_test


try:
    import tket2

    tket2_installed = True
except ImportError:
    tket2_installed = False


path = pathlib.Path(__file__).parent.resolve() / "py_errors"
files = [
    x
    for x in path.iterdir()
    if x.is_file()
    if x.suffix == ".py" and x.name not in ("__init__.py", "tket2_not_installed.py")
]

# Turn paths into strings, otherwise pytest doesn't display the names
files = [str(f) for f in files]


@pytest.mark.parametrize("file", files)
def test_py_errors(file, capsys):
    run_error_test(file, capsys)


@pytest.mark.skipif(tket2_installed, reason="tket2 is installed")
def test_tket2_not_installed(capsys):
    path = pathlib.Path(__file__).parent.resolve() / "py_errors" / "tket2_not_installed.py"
    run_error_test(str(path), capsys)
