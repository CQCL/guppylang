from tempfile import NamedTemporaryFile
from pathlib import Path
import subprocess
import json
from guppy.compiler import guppy, GuppyModule
from guppy.hugr.visualise import hugr_to_graphviz

from guppy.prelude.quantum import Qubit

import guppy.prelude.quantum as quantum
from guppy.prelude.quantum import h, cx, measure, rz
from pecos.engines.hybrid_engine import HybridEngine
from pecos.simulators.quantum_simulator import QuantumSimulator

HUGR2PHIR = Path("../tket2proto/target/debug/hugr2phir")
PHIR_CLI = Path("../phir/.devenv/state/venv/bin/phir-cli")

module = GuppyModule("test")
module.load(quantum)


@guppy(module)
def main(q1: Qubit, q2: Qubit) -> tuple[Qubit, Qubit, bool, bool, int]:
    # q1 = rz(q1, 0.1)
    q1, q2 = cx(h(q1), q2)
    q1, b1 = measure(q1)
    q2, b2 = measure(q2)
    a = 3 + 2 * 5
    return q1, q2, b1, b2, a


hugr = module.compile(True)
hugr_to_graphviz(hugr).render("dump/hugr", format="pdf")
assert hugr is not None


def convert_bitstrings(res: dict[str, list[str]]) -> dict[str, list[int]]:
    return {k: [int(x, 2) for x in vs]  for k, vs in res.items ()}
with NamedTemporaryFile("wb", suffix="hugr") as h_file, NamedTemporaryFile(
    suffix="json"
) as ph_file:
    h_file.write(hugr.serialize())
    h_file.flush()

    subprocess.run([str(c) for c in (HUGR2PHIR, h_file.name, "-o", ph_file.name)]).check_returncode()
    subprocess.run([str(c) for c in (PHIR_CLI, ph_file.name)]).check_returncode()

    phir_json = json.load(ph_file)
    # with open("../PECOS/tests/integration/phir/example1_no_wasm.json") as j:
    #     phir_json = json.load(j)
    print(phir_json)
    res = HybridEngine(qsim=QuantumSimulator()).run(program=phir_json, shots=10)
    print(convert_bitstrings(res))
# TODO simulate with pecos
