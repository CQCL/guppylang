from guppylang.decorator import guppy


@guppy
def test() -> int:
    with power(1):
        x = 1
    return x + 2


test.compile()
