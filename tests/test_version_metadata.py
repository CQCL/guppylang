from guppylang_internals.engine import CoreMetadataKeys

from guppylang import __version__, guppy


def test_metadata():
    @guppy
    def foo() -> None:
        pass

    hugr = foo.compile().modules[0]
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
