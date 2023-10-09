from guppy.compiler import GuppyModule
from guppy.prelude.quantum import Qubit

import guppy.prelude.quantum as quantum
import guppy.prelude.qref as qref

from guppy.prelude.qref import h, cx, ref, deref, initmem


def test_id(validate):
    module = GuppyModule("test")
    module.load(quantum)
    module.load(qref)

    @module
    def test(q: Qubit) -> Qubit:
        return deref(ref(q))

    validate(module.compile(True))


def test_ops(validate):
    module = GuppyModule("test")
    module.load(quantum)
    module.load(qref)

    @module
    def test(q1: Qubit, q2: Qubit) -> tuple[Qubit, Qubit]:
        r1, r2 = ref(q1), ref(q2)
        h(r1)
        cx(r2, r1)
        cx(r1, r2)
        h(r2)
        h(r1)
        return deref(r1), deref(r2)

    validate(module.compile(True))


def test_if1(validate):
    module = GuppyModule("test")
    module.load(quantum)
    module.load(qref)

    @module
    def test(b: bool, q: Qubit) -> Qubit:
        initmem()
        r = ref(q)
        if b:
            h(r)
            h(r)
            h(r)
        return deref(r)

    validate(module.compile(True))


def test_if2(validate):
    module = GuppyModule("test")
    module.load(quantum)
    module.load(qref)

    @module
    def test(b: bool, q1: Qubit, q2: Qubit) -> tuple[Qubit, Qubit]:
        initmem()
        r1, r2 = ref(q1), ref(q2)
        cx(r1, r2)
        if b:
            h(r1)
        else:
            h(r2)
        cx(r1, r2)
        return deref(r1), deref(r2)

    validate(module.compile(True))


def test_if3(validate):
    module = GuppyModule("test")
    module.load(quantum)
    module.load(qref)

    @module
    def test(b: bool, q1: Qubit, q2: Qubit) -> tuple[Qubit, Qubit]:
        initmem()
        r1, r2 = ref(q1), ref(q2)
        cx(r1, r2)
        h(r1 if b else r2)
        cx(r1, r2)
        return deref(r1), deref(r2)

    validate(module.compile(True))
