from guppylang.decorator import guppy


# TODO: The error message is confusing.
@guppy
def test() -> None:
    with power(1) as x:
        pass


test.compile()
