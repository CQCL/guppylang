from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import inout
from guppylang.prelude.quantum import qubit

import guppylang.prelude.quantum as quantum


def test_declare(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy.declare(module)
    def test(q: qubit @inout) -> qubit: ...

    validate(module.compile())


def test_string_annotation(validate):
    module = GuppyModule("test")
    module.load(quantum)

    @guppy.declare(module)
    def test(q: "qubit @inout") -> qubit: ...

    validate(module.compile())
