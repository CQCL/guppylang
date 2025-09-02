from guppylang import guppy
from guppylang_internals.decorator import lowerable_op
from guppylang.std.quantum import qubit, h, cx, measure

import hugr.ext as he

from pydantic_extra_types.semantic_version import SemanticVersion


def test_auto_hugr_lowering(validate):
    test_hugr_ext = he.Extension("test_hugr_ext", SemanticVersion(0, 1, 0))

    @lowerable_op(test_hugr_ext)
    def entangle(q0: qubit, q1: qubit) -> None:
        h(q0)
        cx(q0, q1)

    @guppy
    def main() -> None:
        q0 = qubit()
        q1 = qubit()
        q2 = qubit()
        entangle(q0, q1)
        entangle(q1, q2)
        measure(q0)
        measure(q1)
        measure(q2)

    hugr = main.compile()

    hugr.extensions.append(test_hugr_ext)

    validate(hugr)


def test_lower_funcs_hugr(validate):
    test_hugr_ext = he.Extension("test_hugr_ext", SemanticVersion(0, 1, 0))

    @lowerable_op(test_hugr_ext)
    def entangle(q0: qubit, q1: qubit) -> None:
        h(q0)
        cx(q0, q1)

    op = test_hugr_ext.get_op("entangle")

    for funcs in op.lower_funcs:
        validate(funcs.hugr)
