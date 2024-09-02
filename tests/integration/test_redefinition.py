from guppylang.decorator import guppy
from guppylang.module import GuppyModule

import guppylang.prelude.quantum as quantum


def test_redefinition(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy(module)
    def test() -> bool:
        return True

    @guppy(module)
    def test() -> bool:  # noqa: F811
        return False

    validate(module.compile())
