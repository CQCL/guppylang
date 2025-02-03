from typing import no_type_check

from hugr.package import ModulePointer

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std import quantum
from guppylang.std.builtins import array, py
from guppylang.std.quantum import cx, discard_array, h, qubit


def big_array_module(n_q: int = 20, n_a: int = 5) -> ModulePointer:
    module = GuppyModule("big_array")
    module.load_all(quantum)

    @guppy(module)
    @no_type_check
    def main() -> array[qubit, py(n_q)]:
        q = array(qubit() for _ in range(py(n_q)))
        a = array(array(qubit() for _ in range(py(n_a))) for _ in range(py(n_q)))
        h(a[7][2])
        h(a[3][3])
        h(a[15][1])
        h(a[2][0])
        h(a[0][3])
        h(a[17][2])
        h(a[1][1])
        h(a[16][4])
        h(a[11][2])
        h(a[5][0])
        h(a[8][1])
        h(a[0][2])
        h(a[8][1])
        h(a[5][2])
        h(a[9][2])
        h(a[2][4])
        h(a[10][3])
        h(a[16][1])
        h(a[5][1])
        h(a[15][2])
        h(a[2][4])
        h(a[9][0])
        h(a[9][4])
        h(a[9][4])
        h(a[6][3])
        h(a[13][4])
        h(a[9][3])
        h(a[14][1])
        h(a[7][2])
        h(a[8][0])
        cx(q[2], a[1][3])
        cx(q[8], a[16][4])
        cx(q[15], a[10][1])
        cx(q[6], a[2][3])
        cx(q[6], a[14][2])
        cx(q[5], a[11][3])
        cx(q[18], a[10][4])
        cx(q[6], a[10][0])
        cx(q[1], a[7][2])
        cx(q[18], a[19][1])
        cx(q[3], a[10][1])
        cx(q[9], a[14][0])
        cx(q[1], a[11][0])
        cx(q[9], a[10][0])
        cx(q[10], a[9][2])
        cx(q[4], a[13][4])
        cx(q[2], a[9][4])
        cx(q[6], a[14][2])
        cx(q[4], a[8][3])
        cx(q[19], a[5][2])
        cx(q[18], a[0][2])
        cx(q[1], a[14][1])
        cx(q[11], a[11][2])
        cx(q[18], a[3][3])
        cx(q[6], a[13][1])
        cx(q[3], a[1][0])
        cx(q[1], a[5][4])
        cx(q[4], a[19][0])
        cx(q[17], a[15][4])
        cx(q[7], a[10][0])
        cx(q[3], a[16][2])
        cx(q[13], a[6][3])
        cx(q[6], a[7][3])
        cx(q[13], a[15][0])
        cx(q[7], a[13][3])
        cx(q[7], a[13][1])
        cx(q[15], a[6][0])
        cx(q[1], a[8][2])
        cx(q[7], a[16][1])
        cx(q[7], a[13][2])
        cx(q[4], a[10][0])
        cx(q[10], a[18][0])
        cx(q[18], a[12][0])
        cx(q[15], a[12][0])
        cx(q[13], a[6][4])
        cx(q[5], a[10][2])
        cx(q[15], a[10][3])
        cx(q[16], a[6][2])
        cx(q[10], a[12][3])
        cx(q[2], a[8][1])
        cx(q[1], a[12][4])
        cx(q[4], a[8][0])
        cx(q[5], a[14][4])
        cx(q[15], a[12][3])
        cx(q[6], a[0][1])
        cx(q[5], a[0][4])
        cx(q[8], a[3][3])
        cx(q[12], a[7][4])
        cx(q[1], a[6][1])
        cx(q[19], a[10][4])
        cx(q[15], a[16][3])
        cx(q[0], a[2][0])
        cx(q[19], a[3][3])
        cx(q[17], a[8][4])
        cx(q[4], a[1][2])
        cx(q[2], a[16][0])
        cx(q[9], a[11][0])
        cx(q[2], a[17][3])
        cx(q[12], a[6][2])
        cx(q[12], a[7][3])
        cx(q[12], a[3][0])
        cx(q[3], a[19][2])
        cx(q[16], a[13][3])
        cx(q[14], a[2][1])
        cx(q[9], a[15][3])
        cx(q[3], a[17][1])
        cx(q[11], a[5][1])
        cx(q[4], a[10][3])
        cx(q[10], a[8][4])
        cx(q[0], a[5][0])
        cx(q[9], a[3][4])
        cx(q[3], a[15][4])
        cx(q[15], a[16][0])
        cx(q[16], a[7][3])
        cx(q[9], a[11][1])
        cx(q[5], a[0][0])
        cx(q[19], a[10][4])
        cx(q[14], a[18][2])
        cx(q[16], a[14][4])
        cx(q[19], a[14][3])
        cx(q[4], a[8][4])
        cx(q[11], a[10][1])
        cx(q[13], a[2][4])
        cx(q[4], a[19][1])
        cx(q[9], a[11][1])
        cx(q[18], a[11][4])
        cx(q[2], a[2][3])
        cx(q[5], a[10][2])
        cx(q[10], a[5][2])
        cx(q[0], a[19][0])
        cx(q[16], a[2][2])
        cx(q[3], a[5][1])
        cx(q[18], a[15][4])
        cx(q[2], a[3][1])
        cx(q[15], a[7][4])
        cx(q[9], a[12][4])
        cx(q[7], a[15][1])
        cx(q[9], a[11][1])
        cx(q[10], a[17][4])
        cx(q[14], a[12][4])
        cx(q[12], a[10][2])
        cx(q[14], a[13][4])
        cx(q[0], a[8][1])
        cx(q[17], a[14][4])
        cx(q[19], a[11][3])
        cx(q[12], a[19][0])
        cx(q[4], a[16][0])
        cx(q[14], a[11][4])
        cx(q[9], a[2][2])
        cx(q[15], a[7][3])
        cx(q[19], a[2][1])
        cx(q[7], a[2][2])
        cx(q[4], a[1][1])
        cx(q[12], a[18][4])
        cx(q[17], a[17][2])
        cx(q[0], a[16][1])
        cx(q[5], a[3][1])
        cx(q[1], a[10][0])
        cx(q[3], a[8][0])
        cx(q[9], a[19][1])
        cx(q[4], a[13][1])
        cx(q[2], a[17][2])
        cx(q[0], a[17][1])
        cx(q[16], a[13][1])
        cx(q[6], a[9][3])
        cx(q[16], a[2][3])
        cx(q[5], a[5][2])
        cx(q[16], a[12][4])
        cx(q[9], a[12][2])
        cx(q[5], a[12][0])
        cx(q[13], a[0][2])
        cx(q[0], a[9][1])
        cx(q[2], a[5][0])
        cx(q[19], a[0][1])
        cx(q[7], a[17][0])
        cx(q[15], a[17][1])
        cx(q[14], a[12][2])
        cx(q[5], a[16][4])
        cx(q[6], a[3][3])
        cx(q[19], a[11][2])
        cx(q[13], a[19][0])
        cx(q[6], a[8][4])
        cx(q[18], a[9][3])
        cx(q[10], a[2][1])
        cx(q[10], a[3][0])
        cx(q[19], a[10][4])
        cx(q[15], a[11][0])
        cx(q[5], a[1][3])
        cx(q[16], a[17][4])
        cx(q[7], a[1][1])
        cx(q[2], a[10][4])
        cx(q[4], a[9][0])
        cx(q[16], a[16][0])
        cx(q[2], a[7][4])
        cx(q[8], a[19][0])
        cx(q[1], a[0][3])
        cx(q[4], a[6][2])
        cx(q[7], a[11][2])
        cx(q[12], a[19][3])
        cx(q[1], a[5][3])
        cx(q[15], a[2][4])
        cx(q[16], a[9][4])
        cx(q[9], a[6][3])
        cx(q[10], a[5][1])
        cx(q[0], a[15][3])
        cx(q[8], a[10][3])
        cx(q[13], a[10][4])
        cx(q[6], a[8][2])
        cx(q[16], a[2][0])
        cx(q[12], a[8][4])
        cx(q[9], a[4][4])
        cx(q[10], a[2][1])
        cx(q[19], a[2][1])
        cx(q[8], a[6][3])
        cx(q[3], a[10][0])
        cx(q[14], a[18][1])
        cx(q[5], a[2][1])
        cx(q[16], a[3][0])
        cx(q[10], a[9][4])
        cx(q[18], a[4][0])
        cx(q[5], a[0][1])
        cx(q[6], a[8][0])
        cx(q[18], a[10][2])
        cx(q[19], a[11][1])
        cx(q[5], a[6][0])
        cx(q[1], a[5][0])
        cx(q[8], a[15][0])
        cx(q[6], a[4][3])
        cx(q[15], a[19][4])
        cx(q[15], a[17][2])
        for b in a:
            discard_array(b)
        return q

    return module.compile()


def test_big_arrays(benchmark) -> None:
    hugr: ModulePointer = benchmark(big_array_module)
    benchmark.extra_info["nodes"] = hugr.module.num_nodes()
