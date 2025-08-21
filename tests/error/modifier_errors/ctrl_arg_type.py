from guppylang.decorator import guppy


@guppy
def test() -> None:
    with control(True):
        pass


test.compile()
