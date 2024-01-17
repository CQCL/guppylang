from guppylang.decorator import guppy


@guppy(compile=True)
def foo() -> int:
    def bar() -> int:
        return x

    return bar()
