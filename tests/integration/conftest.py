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
        js = hugr.serialize()
        validate_json(js)

        if export_test_cases_dir:
            file_name = f"{request.node.name}{f'_{name}' if name else ''}.json"
            export_file = export_test_cases_dir / file_name
            export_file.write_text(js)

    return validate_impl
