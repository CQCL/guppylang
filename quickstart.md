Guppy is a quantum programming language that is fully embedded into Python. It
allows you to write high-level hybrid quantum programs with classical control
flow and mid-circuit measurements using Pythonic syntax:

```python
from guppylang import guppy
from guppylang.prelude.quantum import cx, h, measure, qubit, x, z

@guppy
def teleport(src: qubit, tgt: qubit) -> qubit:
    """Teleports the state in `src` to `tgt`."""
    # Create ancilla and entangle it with src and tgt
    tmp = qubit()
    tmp, tgt = cx(h(tmp), tgt)
    src, tmp = cx(src, tmp)

    # Apply classical corrections
    if measure(h(src)):
        tgt = z(tgt)
    if measure(tmp):
        tgt = x(tgt)
    return tgt

guppy.compile_module()
```
