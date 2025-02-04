import pytest

from guppylang.decorator import guppy
from guppylang.module import GuppyModule


def test_wrong_module():
    module1 = GuppyModule("module1")
    module2 = GuppyModule("module2")

    @guppy.declare(module1)
    def foo() -> int: ...

    @guppy.comptime(module2)
    def main() -> int:
        return foo()

    err = (
        "Function `foo` is not available in this module, consider importing it from "
        "`module1`"
    )
    with pytest.raises(TypeError, match=err):
        module2.compile()
