from hugr import Hugr

from pathlib import Path
import pytest


@pytest.fixture()
def export_test_cases_dir(request):
    r = request.config.getoption("--export-test-cases")
    if r and not r.exists():
        r.mkdir(parents=True)
    return r


@pytest.fixture()
def validate(request, export_test_cases_dir: Path):
    def validate_json(hugr: str):
        try:
            import guppyval

            guppyval.validate_json(hugr)
        except ImportError:
            pytest.skip("Skipping validation")

    def validate_impl(hugr, name=None):
        # Validate via the json encoding
        js = hugr.to_serial().to_json()
        validate_json(js)

        if export_test_cases_dir:
            file_name = f"{request.node.name}{f'_{name}' if name else ''}.json"
            export_file = export_test_cases_dir / file_name
            export_file.write_text(js)

    return validate_impl


class LLVMException(Exception):
    pass


@pytest.fixture()
def run_int_fn():
    def f(hugr: Hugr, expected: int, fn_name: str = "main"):
        try:
            import execute_llvm

            if not hasattr(execute_llvm, "run_int_function"):
                pytest.skip("Skipping llvm execution")

            hugr_json: str = hugr.to_serial().to_json()
            res = execute_llvm.run_int_function(hugr_json, fn_name)
            if res != expected:
                raise LLVMException(
                    f"Expected value ({expected}) doesn't match actual value ({res})"
                )
        except ImportError:
            pytest.skip("Skipping llvm execution")

    return f
