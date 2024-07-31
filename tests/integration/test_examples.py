import math
from collections.abc import Callable

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import result, py
from guppylang.prelude.quantum import qubit

import guppylang.prelude.quantum as quantum
from guppylang.prelude.quantum import h, discard, cx, x, measure, rz


def test_random_walk_phase_estimation(validate):
    # Implementation of the adaptive random walk phase estimation algorithm from
    # https://arxiv.org/abs/2208.04526 that uses branching on mid-circuit measurements
    # and dynamic rotation angles. The example Hamiltonian and numbers are taken from
    # https://arxiv.org/abs/2206.12950

    module = GuppyModule("test")
    module.load(quantum)

    sqrt_e = math.sqrt(math.e)
    sqrt_e_div = math.sqrt((math.e - 1) / math.e)

    @guppy(module)
    def random_walk_phase_estimation(
        eigenstate: Callable[[], qubit],
        controlled_oracle: Callable[[qubit, qubit, float], tuple[qubit, qubit]],
        num_iters: int,
        reset_rate: int,
        mu: float,
        sigma: float,
    ) -> float:
        """Performs the random walk phase estimation algorithm on a single qubit for
        some Hamiltonian H.

        Arguments:
           eigenstate: Function preparing the eigenstate of e^itH
           controlled_oracle: The oracle circuit for a controlled e^itH
           num_iters: Number of iterations to run the algorithm for
           reset_rate: Reset the eigenstate every x iterations
           mu: Initial mean for the eigenvalue estimate
           sigma: Initial standard deviation for the eigenvalue estimate
        """
        tgt = eigenstate()
        i = 0
        while i < num_iters:
            aux = h(qubit())
            t = 1 / sigma
            aux = rz(h(aux), (sigma - mu) * t)
            aux, tgt = controlled_oracle(aux, tgt, t)
            if measure(h(aux)):
                mu += sigma / py(sqrt_e)
            else:
                mu -= sigma / py(sqrt_e)
            sigma *= py(sqrt_e_div)

            # Reset the eigenstate every few iterations to increase the fidelity of
            # the algorithm
            if i % reset_rate == 0:
                discard(tgt)
                tgt = eigenstate()
            i += 1
        discard(tgt)
        return mu

    @guppy(module)
    def example_controlled_oracle(
        q1: qubit, q2: qubit, t: float
    ) -> tuple[qubit, qubit]:
        """A controlled e^itH gate for the example Hamiltonian H = -0.5 * Z"""
        # This is just a controlled rz gate
        angle = -0.5 * t
        q2 = rz(q2, angle / 2)
        q1, q2 = cx(q1, q2)
        q2 = rz(q2, -angle / 2)
        return cx(q1, q2)

    @guppy(module)
    def example_eigenstate() -> qubit:
        """The eigenstate of e^itH for the example Hamiltonian H = -0.5 * Z"""
        # This is just |1>
        return x(qubit())

    @guppy(module)
    def main() -> int:
        num_iters = 24  # To avoid underflows
        reset_rate = 8
        mu = py(sqrt_e)
        sigma = py(sqrt_e_div)
        eigenvalue = random_walk_phase_estimation(
            example_eigenstate,
            example_controlled_oracle,
            num_iters,
            reset_rate,
            mu,
            sigma,
        )
        result(0, eigenvalue)  # Expected outcome is 0.5
        return 0

    validate(module.compile())
