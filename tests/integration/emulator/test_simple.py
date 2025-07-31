from guppylang.decorator import guppy
from guppylang.std.builtins import result
from guppylang.std.quantum import qubit, measure, h
from guppylang.emulator import QsysResult, EmulatorOpts


def test_basic_emulation() -> None:
    @guppy
    def main() -> None:
        result("c", measure(qubit()))

    em = main.build_emulator()
    res = em.run(1, EmulatorOpts.statevector())
    expected = QsysResult([[("c", False)]])
    assert res._qsys_result == expected

    @guppy
    def main() -> None:
        q = qubit()
        h(q)
        result("c", measure(q))

    em = main.build_emulator()
    res = em.run(1, EmulatorOpts.statevector().with_random_seed(42))
    expected = QsysResult([[("c", True)]])
    assert res._qsys_result == expected
