from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import qubit

import guppylang.prelude.quantum as quantum
from guppylang.prelude.quantum import cx, measure, dirty_qubit


def test_assign(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def test() -> tuple[bool, bool]:
        q1, q2 = qubit(), dirty_qubit()
        q1, q2 = cx(q1, q2)
        return (measure(q1), measure(q2))

    validate(module.compile())
