from guppylang.std.builtins import result, comptime
from tests.util import compile_guppy

TAG_MAX_LEN = 200

@compile_guppy
def foo(y: bool) -> None:    
    result(comptime("a" * (TAG_MAX_LEN + 1)), y)
