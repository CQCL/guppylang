from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import qubit

from guppylang.prelude.quantum import dirty_qubit, quantum, measure
from guppylang.prelude.quantum_functional import cx


def test_dirty_qubit(validate):
    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy(module)
    def test() -> tuple[bool, bool]:
        q1, q2 = qubit(), dirty_qubit()
        q1, q2 = cx(q1, q2)
        return (measure(q1), measure(q2))

    validate(module.compile())
