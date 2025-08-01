from hugr import Hugr
from hugr.package import Package, PackagePointer

from pathlib import Path
import pytest
from typing import Any

from selene_hugr_qis_compiler import check_hugr

from guppylang.defs import GuppyDefinition


@pytest.fixture(scope="session")
def export_test_cases_dir(request):
    r = request.config.getoption("--export-test-cases")
    if r and not r.exists():
        r.mkdir(parents=True)
    return r


@pytest.fixture(scope="session")
def validate(request, export_test_cases_dir: Path):
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

        check_hugr(package_bytes)

    return validate_impl


class LLVMException(Exception):
    pass


def _emulate_fn(is_flt: bool = False):
    """Use selene to emulate a Guppy function."""
    from guppylang.decorator import guppy
    from guppylang.std.builtins import result

    def f(f: GuppyDefinition, expected: Any, args: list[Any] | None = None):
        args = args or []

        @guppy.comptime
        def int_entry() -> None:
            o: int = f(*args)
            result("_test_output", o)

        @guppy.comptime
        def flt_entry() -> None:
            o: float = f(*args)
            result("_test_output", o)

        entry = flt_entry if is_flt else int_entry
        res = entry.emulator(0).coinflip_sim().with_seed(42).run()
        num = next(v for k, v in res.results[0].entries if k == "_test_output")
        if num != expected:
            raise LLVMException(
                f"Expected value ({expected}) doesn't match actual value ({num})"
            )

    return f


@pytest.fixture
def run_int_fn():
    """Emulate an integer function using the Guppy emulator."""
    return _emulate_fn(is_flt=False)


@pytest.fixture
def run_float_fn_approx():
    """Like run_int_fn, but takes optional additional parameters `rel`, `abs`
    and `nan_ok` as per `pytest.approx`."""
    run_fn = _emulate_fn(is_flt=True)

    def run_approx(
        f: GuppyDefinition,
        expected: float,
        args: list[Any] | None = None,
        *,
        rel: float | None = None,
        abs: float | None = None,
        nan_ok: bool = False,
    ):
        return run_fn(
            f,
            pytest.approx(expected, rel=rel, abs=abs, nan_ok=nan_ok),
            args,
        )

    return run_approx
