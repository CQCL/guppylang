from guppylang import guppy, __version__

def test_metadata():
    @guppy
    def foo() -> None:
        pass

    hugr = foo.compile().module
    assert hugr.entrypoint.metadata['guppy_version'] == __version__
