from guppylang.decorator import guppy
from guppylang.std.builtins import result
from guppylang.std.quantum import qubit, measure, h
from guppylang.emulator import EmulatorResult


def test_basic_emulation() -> None:
    @guppy
    def main() -> None:
        result("c", measure(qubit()))

    res = main.emulator(1).run()
    expected = EmulatorResult([[("c", False)]])
    assert res == expected

    @guppy
    def main() -> None:
        q = qubit()
        h(q)
        result("c", measure(q))

    res = main.emulator(1).statevector_sim().with_seed(42).run()
    expected = EmulatorResult([[("c", True)]])
    assert res == expected


# TODO more tests
