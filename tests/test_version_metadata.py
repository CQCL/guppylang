from guppylang import guppy, __version__

def test_metadata():
    @guppy
    def foo() -> None:
        pass

    hugr = foo.compile().module
    assert hugr.module_root.metadata["__generator"]["name"] == "guppy"
    assert hugr.module_root.metadata["__generator"]["version"] == __version__
