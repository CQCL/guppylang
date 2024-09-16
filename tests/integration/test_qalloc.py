from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import qubit

from guppylang.prelude.quantum import dirty_qubit, measure
from guppylang.prelude.quantum_functional import cx

import guppylang.prelude.quantum_functional as quantum_functional


def test_dirty_qubit(validate):
    module = GuppyModule("test")
    module.load_all(quantum_functional)
    module.load(qubit, dirty_qubit, measure)

    @guppy(module)
    def test() -> tuple[bool, bool]:
        q1, q2 = qubit(), dirty_qubit()
        q1, q2 = cx(q1, q2)
        return (measure(q1), measure(q2))

    validate(module.compile())
