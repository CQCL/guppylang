import numpy as np

from guppylang.decorator import guppy
from guppylang.prelude.angles import angle, pi
from guppylang.prelude.builtins import linst, py
from guppylang.prelude.quantum import (
    cz,
    discard,
    h,
    measure,
    qubit,
    rx,
    rz,
)


phi = np.arccos(1 / 3)


@guppy
def ry(q: qubit, theta: angle) -> qubit:
    q = rx(q, pi / 2)
    q = rz(q, theta + pi)
    q = rx(q, pi / 2)
    return rz(q, pi)


# Preparation of approximate T state, from https://arxiv.org/abs/2310.12106
@guppy
def prepare_approx(q: qubit) -> qubit:
    q = ry(q, angle(py(phi)))
    return rz(q, pi / 4)


# The inverse of the [[5,3,1]] encoder in figure 3 of https://arxiv.org/abs/2208.01863
@guppy
def distill(
    target: qubit, q0: qubit, q1: qubit, q2: qubit, q3: qubit
) -> tuple[qubit, bool]:
    """First argument is the target qubit which will be returned from the circuit.
    Other arguments are ancillae, which should also be in an approximate T state.
    Returns target qubit and a bool, which is true if the distillation succeeded.
    """
    q0, q1 = cz(q0, q1)
    q2, q3 = cz(q2, q3)
    target, q0 = cz(target, q0)
    q1, q2 = cz(q1, q2)
    target, q3 = cz(target, q3)
    # Measuring gives false for success, true for failure.
    # We check for all falses to say whether distillation succeeded.
    bits = [not (measure(h(q))) for q in [q0, q1, q2, q3]]
    # guppy doesn't yet support the `any` or `all` operators...
    success = True
    for b in bits:
        success &= b
    return target, success


@guppy
def t_state(timeout: int) -> tuple[linst[qubit], bool]:
    """Create a T state using magic state distillation with `timeout` attempts.

    On success returns a singleton `linst` containing a qubit in a magic T state
    and the boolean `True`.

    If the number of attempts is exceeded, the empty `linst` will be returned
    along with the boolean `False`.
    """
    if timeout > 0:
        tgt = prepare_approx(qubit())
        q0 = prepare_approx(qubit())
        q1 = prepare_approx(qubit())
        q2 = prepare_approx(qubit())
        q3 = prepare_approx(qubit())

        q, success = distill(tgt, q0, q1, q2, q3)
        if success:
            return [q], True
        else:
            # Discard the qubit and start over
            # Note, this could just as easily be a while loop!
            discard(q)
            return t_state(timeout - 1)

    # We ran out of attempts
    return [], False


hugr = guppy.compile_module()
