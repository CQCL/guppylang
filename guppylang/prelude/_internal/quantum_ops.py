"""Manual instantiation functions for hugr standard operations

We should be able to remove the signature definition redundancies after
https://github.com/CQCL/hugr/issues/1512
"""

from .json_defs import load_extension

FUTURES_EXTENSION = load_extension("tket2.futures")
HSERIES_EXTENSION = load_extension("tket2.hseries")
QUANTUM_EXTENSION = load_extension("tket2.quantum")
RESULT_EXTENSION = load_extension("tket2.result")


TKET2_EXTENSIONS = [
    FUTURES_EXTENSION,
    HSERIES_EXTENSION,
    QUANTUM_EXTENSION,
    RESULT_EXTENSION,
]


ANGLE_T = QUANTUM_EXTENSION.get_type("angle")
