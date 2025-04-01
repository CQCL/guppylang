from guppylang.std.builtins import state_result
from guppylang.std.quantum import qubit, discard
from tests.integration.test_quantum import compile_quantum_guppy


def test_basic(validate):
    @compile_quantum_guppy
    def main() -> None:
        q1 = qubit()
        q2 = qubit()
        state_result("tag", q1, q2)
        discard(q1)
        discard(q2)

    validate(main)