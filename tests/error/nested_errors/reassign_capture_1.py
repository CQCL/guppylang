from guppy.decorator import guppy


@guppy(compile=True)
def foo(x: int) -> int:
    y = x + 1

    def bar() -> None:
        y += 2

    bar()
    return y
