from hugr import Hugr
from hugr.ext import Package

from pathlib import Path
import pytest
import subprocess
from typing import Any


@pytest.fixture(scope="session")
def export_test_cases_dir(request):
    r = request.config.getoption("--export-test-cases")
    if r and not r.exists():
        r.mkdir(parents=True)
    return r


def get_validator() -> Path | None:
    """
    Returns the path to the `validator` binary, if it exists.
    Otherwise, returns `None`.
    """
    bin_path = Path(__file__).parent.parent.parent / "target" / "release" / "validator"
    if bin_path.exists():
        return bin_path

    return None


@pytest.fixture(scope="session")
def validate(request, export_test_cases_dir: Path):
    if request.config.getoption("validation"):
        # Check if the validator is installed
        validator = get_validator()
        if validator is None:
            pytest.fail("Run `cargo build -p release` to install the validator")
    else:
        pytest.skip("Skipping validation tests as requested")

    def validate_json(hugr: str):
        # Executes `cargo run -p validator -- validate -`
        # passing the hugr JSON as stdin
        p = subprocess.run(  # noqa: S603
            [validator, "validate", "-"],
            text=True,
            input=hugr,
            capture_output=True,
        )

        if p.returncode != 0:
            raise RuntimeError(f"{p.stderr}")

    def validate_impl(hugr: Package | Hugr, name=None):
        # Validate via the json encoding
        js = hugr.to_json()

        if export_test_cases_dir:
            file_name = f"{request.node.name}{f'_{name}' if name else ''}.json"
            export_file = export_test_cases_dir / file_name
            export_file.write_text(js)

        validate_json(js)

    return validate_impl


class LLVMException(Exception):
    pass


def _run_fn(run_fn_name: str):
    def f(hugr: Package, expected: Any, fn_name: str = "main"):
        try:
            import execute_llvm

            fn = getattr(execute_llvm, run_fn_name)
            if not fn:
                pytest.skip("Skipping llvm execution")

            hugr_json: str = hugr.modules[0].to_json()
            res = fn(hugr_json, fn_name)
            if res != expected:
                raise LLVMException(
                    f"Expected value ({expected}) doesn't match actual value ({res})"
                )
        except ImportError:
            pytest.skip("Skipping llvm execution")

    return f



@pytest.fixture
def run_int_fn():
    return _run_fn("run_int_function")

@pytest.fixture
def run_float_fn():
    return _run_fn("run_float_function")
