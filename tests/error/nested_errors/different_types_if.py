from guppylang.decorator import guppy


@guppy
def foo(b: bool) -> int:
    if b:
        def bar() -> int:
            return 0
    else:
        def bar() -> bool:
            return False

    return bar()
