import pytest

from . import util

@pytest.fixture
def export_test_cases_dir(request):
    r = request.config.getoption('--export-test-cases')
    if r and not r.exists():
        r.mkdir(parents=True)
    return r


@pytest.fixture
def validate(request, export_test_cases_dir):
    def validate_impl(hugr):
        bs = hugr.serialize()
        util.validate_bytes(bs)
        if export_test_cases_dir:
            export_file = export_test_cases_dir / f"{request.node.name}.msgpack"
            export_file.write_bytes(bs)
    return validate_impl
