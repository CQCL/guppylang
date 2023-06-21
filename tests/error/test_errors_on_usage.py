import pathlib
import pytest

from tests.error.util import run_error_test

path = pathlib.Path(__file__).parent.resolve() / "errors_on_usage"
files = [x for x in path.iterdir() if x.is_file() if x.suffix == ".py" and x.name != "__init__.py"]


@pytest.mark.parametrize("file", files)
def test_errors_on_usage(file, capsys):
    run_error_test(file, capsys)
