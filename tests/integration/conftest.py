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
    def validate_impl(hugr,name=None):
        bs = hugr.serialize()
        util.validate_bytes(bs)
        if export_test_cases_dir:
            file_name = f"{request.node.name}{f'_{name}' if name else ''}.msgpack"
            export_file = export_test_cases_dir / file_name
            export_file.write_bytes(bs)
    return validate_impl
