import numpy as np

from guppylang.decorator import guppy
from guppylang.std.angles import angle, pi
from guppylang.std.builtins import array, owned, py
from guppylang.std.option import Option, nothing, some
from guppylang.std.quantum import (
    cz,
    discard,
    h,
    measure,
    qubit,
    ry,
    rz,
)

phi = np.arccos(1 / 3)


# Preparation of approximate T state, from https://arxiv.org/abs/2310.12106
@guppy
def prepare_approx() -> qubit:
    q = qubit()
    ry(q, angle(py(phi)))
    rz(q, pi / 4)
    return q


# The inverse of the [[5,3,1]] encoder in figure 3 of https://arxiv.org/abs/2208.01863
@guppy
def distill(
    target: qubit @ owned,
    qs: array[qubit, 4] @ owned,
) -> tuple[qubit, bool]:
    """First argument is the target qubit which will be returned from the circuit.
    Other arguments are ancillae, which should also be in an approximate T state.
    Returns target qubit and a bool, which is true if the distillation succeeded.
    """
    cz(qs[0], qs[1])
    cz(qs[2], qs[3])
    cz(target, qs[0])
    cz(qs[1], qs[2])
    cz(target, qs[3])
    # Measuring gives false for success, true for failure.
    # We check for all falses to say whether distillation succeeded.
    for i in range(4):
        h(qs[i])
    bits = array(not measure(q) for q in qs)
    # guppy doesn't yet support the `any` or `all` operators...
    success = True
    for b in bits:
        success &= b
    return target, success


@guppy
def t_state(timeout: int) -> Option[qubit]:
    """Create a T state using magic state distillation with `timeout` attempts.

    On success returns a qubit in a magic T state.

    On failure (i.e. number of attempts are exceeded) returns nothing.
    """
    if timeout > 0:
        tgt = prepare_approx()
        qs = array(prepare_approx() for _ in range(4))

        q, success = distill(tgt, qs)
        if success:
            return some(q)
        else:
            # Discard the qubit and start over
            # Note, this could just as easily be a while loop!
            discard(q)
            return t_state(timeout - 1)

    # We ran out of attempts
    return nothing()


hugr = guppy.compile_module()
