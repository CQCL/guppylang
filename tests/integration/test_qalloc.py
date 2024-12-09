from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.quantum import qubit

from guppylang.std.quantum import measure
from guppylang.std.quantum_functional import cx

import guppylang.std.quantum_functional as quantum_functional


def test_qalloc(validate):
    module = GuppyModule("test")
    module.load_all(quantum_functional)
    module.load(qubit, measure)

    @guppy(module)
    def test() -> tuple[bool, bool]:
        q1, q2 = qubit(), qubit()
        q1, q2 = cx(q1, q2)
        return (measure(q1), measure(q2))

    validate(module.compile())
