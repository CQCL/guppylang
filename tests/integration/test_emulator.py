from guppylang.decorator import guppy
from guppylang.std.builtins import result
from guppylang.std.debug import state_result
from guppylang.std.quantum import qubit, measure, h, x
from guppylang.emulator import EmulatorResult
from selene_sim.backends.bundled_runtimes import SoftRZRuntime

from datetime import timedelta
from selene_sim.backends.bundled_simulators import Stim
from selene_sim.backends.bundled_error_models import IdealErrorModel
from selene_sim.event_hooks import NoEventHook


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


def test_all_options() -> None:
    """Test that all configuration options are properly set and accessible."""

    @guppy
    def main() -> None:
        return

    em = main.emulator(1)

    # Test all configuration methods
    configured_em = (
        em.with_shots(100)
        .with_simulator(Stim())
        .with_runtime(SoftRZRuntime())
        .with_error_model(IdealErrorModel())
        .with_event_hook(NoEventHook())
        .with_verbose(True)
        .with_timeout(timedelta(seconds=30))
        .with_seed(12345)
        .with_shot_offset(10)
        .with_shot_increment(2)
        .with_n_processes(4)
    )

    # Verify all properties are set correctly
    assert configured_em.shots == 100
    assert isinstance(configured_em.simulator, Stim)
    assert isinstance(configured_em.runtime, SoftRZRuntime)
    assert isinstance(configured_em.error_model, IdealErrorModel)
    assert configured_em.verbose is True
    assert configured_em.timeout == timedelta(seconds=30)
    assert configured_em.seed == 12345
    assert configured_em.shot_offset == 10
    assert configured_em.shot_increment == 2
    assert configured_em.n_processes == 4

    result = configured_em.run()
    assert isinstance(result, EmulatorResult)


def test_statevector() -> None:
    @guppy
    def main() -> None:
        q = qubit()
        x(q)
        state_result("s", q)
        state_result("s", q)
        result("c", measure(q))

    res = main.emulator(1).run()
    (shot_states,) = res.partial_states()
    assert len(shot_states) == 2
    assert all(tag == "s" for tag, _ in shot_states)

    assert res.partial_state_dicts() == [{"s": shot_states[0][1]}]
