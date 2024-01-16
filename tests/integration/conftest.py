import pytest

from . import util


@pytest.fixture()
def export_test_cases_dir(request):
    r = request.config.getoption("--export-test-cases")
    if r and not r.exists():
        r.mkdir(parents=True)
    return r


@pytest.fixture()
def validate(request, export_test_cases_dir):
    def validate_impl(hugr, name=None):
        # Validate via the msgpack encoding
        bs = hugr.serialize()
        util.validate_bytes(bs)

        # Validate via the json encoding
        js = hugr.serialize_json()
        util.validate_json(js)

        if export_test_cases_dir:
            file_name = f"{request.node.name}{f'_{name}' if name else ''}.msgpack"
            export_file = export_test_cases_dir / file_name
            export_file.write_bytes(bs)

    return validate_impl
