from guppylang.decorator import guppy
from guppylang.std.builtins import result
from guppylang.std.quantum import qubit, measure, h
from guppylang.emulator import EmulatorResult, EmulatorOpts


def test_basic_emulation() -> None:
    @guppy
    def main() -> None:
        result("c", measure(qubit()))

    em = main.build_emulator()
    res = em.run(1, EmulatorOpts.statevector())
    expected = EmulatorResult([[("c", False)]])
    assert res == expected

    @guppy
    def main() -> None:
        q = qubit()
        h(q)
        result("c", measure(q))

    res = main.run_emulator(1, EmulatorOpts.statevector().with_seed(42))
    expected = EmulatorResult([[("c", True)]])
    assert res == expected


# TODO more tests
