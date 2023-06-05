import importlib.util
import pathlib
import pytest


path = pathlib.Path(__file__).parent.resolve() / "type_errors"
files = [x for x in path.iterdir() if x.is_file() if x.suffix == ".py" and x.name != "__init__.py"]


@pytest.mark.parametrize("file", files)
def test_type_errors(file, capsys):
    spec = importlib.util.spec_from_file_location("test_module", file)
    py_module = importlib.util.module_from_spec(spec)

    with pytest.raises(SystemExit):
        spec.loader.exec_module(py_module)

    err = capsys.readouterr().err

    with open(file.with_suffix(".err")) as f:
        exp_err = f.read()

    exp_err = exp_err.replace("$FILE", str(file))
    assert err == exp_err
