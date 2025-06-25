from sympy import use

from guppylang import __version__, guppy
from guppylang.engine import CoreMetadataKeys


def test_metadata():
    @guppy
    def foo() -> None:
        pass

    hugr = foo.compile().module
    meta = hugr.module_root.metadata
    gen_key = CoreMetadataKeys.GENERATOR.value
    assert meta[gen_key]["name"] == "guppylang"
    assert meta[gen_key]["version"] == __version__

    used_key = CoreMetadataKeys.USED_EXTENSIONS.value
    used = meta[used_key]
    assert len(used) > 0
    assert all("name" in ext and "version" in ext for ext in used)
    assert all(isinstance(ext["name"], str) for ext in used)
    assert all(isinstance(ext["version"], str) for ext in used)
