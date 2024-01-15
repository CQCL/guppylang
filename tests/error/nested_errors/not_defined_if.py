from guppy.decorator import guppy


@guppy(compile=True)
def foo(b: bool) -> int:
    if b:
        def bar() -> int:
            return 0
    return bar()
