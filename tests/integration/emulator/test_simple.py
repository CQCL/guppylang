from guppylang.decorator import guppy
from guppylang.std.builtins import result
from guppylang.std.quantum import qubit, measure, h
from guppylang.emulator import QsysResult


def test_basic_emulation() -> None:
    @guppy
    def main() -> None:
        result("c", measure(qubit()))

    em = main.build_emulator()
    res = em.run_statevector(n_qubits=1)
    expected = QsysResult([[("c", False)]])
    assert res._qsys_result == expected

    @guppy
    def main() -> None:
        q = qubit()
        h(q)
        result("c", measure(q))

    em = main.build_emulator()
    em.set_seed(42)
    res = em.run_statevector(n_qubits=1)
    expected = QsysResult([[("c", True)]])
    assert res._qsys_result == expected
