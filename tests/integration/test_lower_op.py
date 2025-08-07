from guppylang import guppy
from guppylang_internals.decorator import lower_op
from guppylang.std.quantum import qubit, h, cx, measure

import hugr.ext as he

from pydantic_extra_types.semantic_version import SemanticVersion


def test_auto_hugr_lowering(validate):
    test_hugr_ext = he.Extension("test_hugr_ext", SemanticVersion(0, 1, 0))

    @lower_op(test_hugr_ext)
    def entangle(q0: qubit, q1: qubit) -> None:
        h(q0)
        cx(q0, q1)

    @guppy
    def main() -> None:
        q0 = qubit()
        q1 = qubit()
        entangle(q0, q1)
        measure(q0)
        measure(q1)

    hugr = main.compile()

    hugr.extensions.append(test_hugr_ext)

    validate(hugr)
