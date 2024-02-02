import pathlib
import pytest

from guppylang import GuppyModule, guppy
from guppylang.error import GuppyError
from guppylang.gtypes import BoolType
from tests.integration.modules.mod_a import mod_a
from tests.integration.modules.mod_b import mod_b

from tests.error.util import run_error_test


def test_doesnt_exist():
    module = GuppyModule("test")

    with pytest.raises(GuppyError, match="Could not find `h` in module `mod_a`"):
        module.import_(mod_a, "h")


def test_func_already_defined():
    module = GuppyModule("test")

    @guppy(module)
    def f() -> None:
        return

    with pytest.raises(GuppyError, match="Module `test` already contains a function named `f`"):
        module.import_(mod_a, "f")


def test_type_already_defined():
    module = GuppyModule("test")

    @guppy.type(module, BoolType().to_hugr())
    class MyType:
        pass

    with pytest.raises(GuppyError, match="Module `test` already contains a type named `MyType`"):
        module.import_(mod_a, "MyType")


def test_func_already_imported():
    module = GuppyModule("test")
    module.import_(mod_a, "f")

    with pytest.raises(GuppyError, match="A function named `f` has already been imported"):
        module.import_(mod_b, "f")


def test_type_already_imported():
    module = GuppyModule("test")
    module.import_(mod_a, "MyType")

    with pytest.raises(GuppyError, match="A type named `MyType` has already been imported"):
        module.import_(mod_b, "MyType")


def test_already_imported_alias():
    module = GuppyModule("test")
    module.import_(mod_a, "f", alias="h")

    with pytest.raises(GuppyError, match="A function named `h` has already been imported"):
        module.import_(mod_b, "h")


path = pathlib.Path(__file__).parent.resolve() / "import_errors"
files = [
    x
    for x in path.iterdir()
    if x.is_file()
    if x.suffix == ".py" and x.name != "__init__.py"
]

# Turn paths into strings, otherwise pytest doesn't display the names
files = [str(f) for f in files]


@pytest.mark.parametrize("file", files)
def test_import_errors(file, capsys):
    run_error_test(file, capsys)
