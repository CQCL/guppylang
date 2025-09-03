from guppylang.decorator import guppy


# TODO: Currntly, `with power(0.2):` passes typecheck as it only checks numeric type.
@guppy
def test() -> None:
    with power(True):
        pass


test.compile()
