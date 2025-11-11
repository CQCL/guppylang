"""Tests validating the files in the `examples` directory."""

import pytest
from pathlib import Path

notebook_files = list(
    (Path(__file__).parent.parent.parent / "examples").glob("*.ipynb")
)

print(notebook_files)

# Remove long running QAOA notebook from C.I. tests
# Hopefully we can add it back in when we can speed it up.
notebook_files.remove("qaoa_maxcut_example.ipynb")


print(notebook_files)


@pytest.mark.parametrize("notebook", notebook_files)
def test_example_notebooks(nb_regression, notebook: Path):
    nb_regression.diff_ignore += (
        "/metadata/language_info/version",
        "/cells/*/outputs/*/data/image/png",
    )
    nb_regression.check(notebook)


def test_demo_notebook(nb_regression):
    nb_regression.diff_ignore += ("/metadata/language_info/version",)
    nb_regression.check("tests/integration/notebooks/demo.ipynb")


def test_comptime_notebook(nb_regression):
    nb_regression.diff_ignore += ("/metadata/language_info/version",)
    nb_regression.check("tests/integration/notebooks/comptime.ipynb")


def test_misc_notebook_tests(nb_regression):
    nb_regression.diff_ignore += ("/metadata/language_info/version",)
    nb_regression.check("tests/integration/notebooks/misc_notebook_tests.ipynb")
