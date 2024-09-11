from guppylang import guppy


@guppy
def foo() -> int:
    return 1.0


guppy.compile_module()
