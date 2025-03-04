from typing import no_type_check

from guppylang.decorator import guppy
from guppylang.std.builtins import array, py
from guppylang.std.quantum import cx, discard_array, h, measure, project_z, qubit


@guppy
@no_type_check
def many_ctrl_flow() -> None:
    qs = array(qubit() for _ in range(py(20)))

    for i in range(py(20)):
        h(qs[i])

    [q0, *qs0] = qs
    if measure(q0):
        [q1, *qs1] = qs0
        if measure(q1):
            [q2, *qs2] = qs1
            if measure(q2):
                [q3, *qs3] = qs2
                if measure(q3):
                    [q4, *qs4] = qs3
                    if measure(q4):
                        cx(qs4[0], qs4[1])
                    discard_array(qs4)
                else:
                    discard_array(qs3)
            else:
                discard_array(qs2)
        else:
            discard_array(qs1)
    else:
        cx(qs0[1], qs0[2])
        while project_z(qs0[0]):
            while project_z(qs0[1]):
                while project_z(qs0[2]):
                    while project_z(qs0[3]):
                        while project_z(qs0[4]):
                            while project_z(qs0[5]):
                                cx(qs0[1], qs0[2])
        discard_array(qs0)


def test_compile_many_ctrl_flow(benchmark):
    def comp() -> None:
        many_ctrl_flow.compile()

    benchmark(comp)
