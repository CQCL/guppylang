from guppylang.decorator import guppy


@guppy
def test() -> None:
    with power(True):
        pass


test.compile()
