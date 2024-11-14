from guppylang.std.builtins import result, py
from tests.util import compile_guppy

# TODO use this once https://github.com/CQCL/guppylang/issues/599 lands
# from guppylang.prelude._internal.checker import TAG_MAX_LEN
# BIG_TAG = "a" * (TAG_MAX_LEN + 1)

@compile_guppy
def foo(y: bool) -> None:
    # each tick or cross is 3 bytes. The cross sends the tag over the limit.
    result("✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅❌", y)
