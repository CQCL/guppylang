from guppy.compiler import GuppyModule


module = GuppyModule("test")


@module.declare
def foo(x: int) -> int:
    return x


module.compile(True)
