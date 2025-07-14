from guppylang.decorator import guppy
from guppylang.std.quantum import qubit, h, cx, measure

from hugr.ext import Extension

from pydantic_extra_types.semantic_version import SemanticVersion



def test_auto_hugr_lowering(validate):

    test_hugr_ext = Extension("test_hugr_ext", SemanticVersion(0, 1, 0))


    @guppy.lower_op(test_hugr_ext)
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


    validate(hugr)

