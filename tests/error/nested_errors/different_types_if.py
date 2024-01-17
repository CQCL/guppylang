from guppylang.decorator import guppy


@guppy(compile=True)
def foo(b: bool) -> int:
    if b:
        def bar() -> int:
            return 0
    else:
        def bar() -> bool:
            return False

    return bar()
