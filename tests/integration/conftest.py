from hugr import Hugr
from hugr.package import Package, PackagePointer

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

    def validate_bytes(package_bytes: bytes):
        # Executes `cargo run -p validator -- validate -`
        # passing the hugr JSON as stdin
        p = subprocess.run(  # noqa: S603
            [validator, "validate", "-"],
            text=False,
            input=package_bytes,
            capture_output=True,
        )

        if p.returncode != 0:
            raise RuntimeError(f"{p.stderr}")

    def validate_impl(package: Package | PackagePointer | Hugr, name=None):
        if isinstance(package, PackagePointer):
            package = package.package
        if isinstance(package, Hugr):
            package = Package([package])
        # Validate via the json encoding
        package_bytes = package.to_bytes()

        if export_test_cases_dir:
            file_name = f"{request.node.name}{f'_{name}' if name else ''}.hugr"
            export_file = export_test_cases_dir / file_name
            export_file.write_bytes(package_bytes)

        validate_bytes(package_bytes)

    return validate_impl


class LLVMException(Exception):
    pass


def _run_fn(run_fn_name: str):
    def f(module: PackagePointer, expected: Any, fn_name: str = "main", args: list[Any] | None = None):
        try:
            import execute_llvm

            fn = getattr(execute_llvm, run_fn_name)
            if not fn:
                pytest.skip("Skipping llvm execution")

            package_bytes = module.package.to_bytes()
            res = fn(package_bytes, fn_name, args or [])
            if res != expected:
                raise LLVMException(
                    f"Expected value ({expected}) doesn't match actual value ({res})"
                )
        except AttributeError:
            pytest.skip("Skipping llvm execution")
        except ImportError:
            pytest.skip("Skipping llvm execution")

    return f


@pytest.fixture
def run_int_fn():
    return _run_fn("run_int_function")


@pytest.fixture
def run_float_fn_approx():
    """Like run_int_fn, but takes optional additional parameters `rel`, `abs` and `nan_ok`
    as per `pytest.approx`."""
    run_fn = _run_fn("run_float_function")

    def run_approx(
        hugr: PackagePointer,
        expected: float,
        fn_name: str = "main",
        args: list[Any] | None = None,
        *,
        rel: float | None = None,
        abs: float | None = None,
        nan_ok: bool = False,
    ):
        return run_fn(
            hugr,
            pytest.approx(expected, rel=rel, abs=abs, nan_ok=nan_ok),
            fn_name,
            args,
        )

    return run_approx
