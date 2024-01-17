from guppylang.decorator import guppy


@guppy(compile=True)
def foo():
    def bar(x: int) -> int:
        return x
