from modulefinder import ModuleFinder
from typing import no_type_check

from guppylang import decorator
from guppylang.module import GuppyModule
from guppylang.std.builtins import array, owned
from guppylang.std.debug import state_result
from guppylang.std.quantum import qubit, discard, discard_array
from guppylang.std import quantum
from guppylang.std import debug

def compile_debug_guppy(fn) -> ModuleFinder:
    """A decorator that combines @guppy with HUGR compilation.

    Modified version of `tests.util.compile_guppy` that loads the quantum and debug 
    modules.
    """
    assert not isinstance(
        fn,
        GuppyModule,
    ), "`@compile_debug_guppy` does not support extra arguments."

    module = GuppyModule("module")
    module.load(
        qubit, discard, discard_array
    )
    module.load(q=quantum)
    module.load_all(debug)
    decorator.guppy(module)(fn)
    return module.compile()


def test_basic(validate):
    @compile_debug_guppy
    def main() -> None:
        q1 = qubit()
        q2 = qubit()
        state_result("tag", q1, q2)
        discard(q1)
        discard(q2)

    validate(main)


def test_multi(validate):
    @compile_debug_guppy
    @no_type_check
    def main() -> None:
        q1 = qubit()
        q2 = qubit()
        state_result("tag1", q1, q2)
        q.x(q1)
        state_result("tag2", q1)
        discard(q1)
        discard(q2)

    validate(main)


def test_array_access(validate):
    @compile_debug_guppy
    @no_type_check
    def main() -> None:
        qs = array(qubit() for _ in range(4))
        q.h(qs[1])
        q.h(qs[2])
        state_result("a", qs[1], qs[2], qs[3])
        state_result("b", qs[1])
        q.h(qs[3])

        q.cx(qs[1], qs[2])
        state_result("c", qs[2], qs[3])
        q.cx(qs[3], qs[4])
        discard_array(qs)

    validate(main)


def test_struct_access(validate):
    module = GuppyModule("module")
    module.load(state_result)
    module.load(qubit, discard)
    module.load(q=quantum)

    @decorator.guppy.struct(module)
    class S:
        q1: qubit
        q2: qubit
        q3: qubit
        q4: qubit

    @decorator.guppy(module)
    @no_type_check
    def test(qs: S @ owned) -> None:
        q.h(qs.q1)
        q.h(qs.q2)
        state_result("1", qs.q1, qs.q2, qs.q3)
        state_result("2", qs.q1)
        q.h(qs.q3)

        q.cx(qs.q1, qs.q2)
        state_result("3", qs.q2, qs.q3)
        q.cx(qs.q3, qs.q4)

        discard(qs.q1)
        discard(qs.q2)
        discard(qs.q3)
        discard(qs.q4)

    validate(module.compile())


def test_array(validate):
    @compile_debug_guppy
    @no_type_check
    def main() -> None:
        qs = array(qubit() for _ in range(4))
        q.h(qs[1])
        q.h(qs[2])
        q.cx(qs[0], qs[3])
        state_result("tag", qs)
        discard_array(qs)

    validate(main)


def test_generic_array(validate):
    module = GuppyModule("module")
    module.load(state_result)
    module.load(qubit, discard)
    module.load(q=quantum)

    n = decorator.guppy.nat_var("n", module=module)

    @decorator.guppy(module)
    @no_type_check
    def main(qs: array[qubit, n]) -> None:
        q.cx(qs[0], qs[1])
        state_result("tag", qs)

    validate(module.compile())