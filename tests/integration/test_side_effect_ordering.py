"""Tests that the compiler correctly inserts order edges between operations that have
side-effects.
"""

from hugr import ops, Hugr, Node
from hugr.std import PRELUDE

from guppylang import guppy
from guppylang.module import GuppyModule
from guppylang.std._internal.compiler.quantum import RESULT_EXTENSION, QUANTUM_EXTENSION
from guppylang.std.builtins import result, array, owned, panic
from guppylang.std.quantum import qubit, discard, measure


def find_ext_nodes(hugr: Hugr, qualified_name: str) -> list[Node]:
    """Returns all extension nodes in a Hugr that match the given qualified name."""
    return [
        node for node, data in hugr.nodes() if name_matches(data.op, qualified_name)
    ]


def name_matches(op: ops.Op, qualified_name: str) -> bool:
    """Checks if an op is an extension op that matches the given qualified name."""
    match op:
        case ops.ExtOp() as ext_op:
            return ext_op.op_def().qualified_name() == qualified_name
        case ops.Custom(op_name=op_name, extension=extension):
            return qualified_name == (
                f"{extension}.{op_name}" if extension else op_name
            )
        case _:
            return False


def check_order(hugr: Hugr, nodes: list[Node]) -> None:
    """Checks that the provided nodes appear in the specified order in the order-edge
    graph."""
    # Do a DFS traversal of the order edge graph starting at the first node
    stack = [nodes[0]]
    visited = set()
    while stack:
        curr = stack.pop()
        visited.add(curr)
        if curr in nodes:
            # Check this node is the next one in the sequence
            assert curr == nodes.pop(0)
        for n in hugr.outgoing_order_links(curr):
            assert n not in visited, "Order edge graph must be acyclic"
            stack.append(n)
    # Check that all specified nodes occurred in the graph
    assert len(nodes) == 0


def test_result_panic(validate):
    module = GuppyModule("test")

    @guppy(module)
    def test() -> None:
        result("a", True)
        result("b", 10)
        panic("Boo!")
        exit("Foo!", 1)
        result("c", 10.5)

    compiled = module.compile()
    validate(compiled)

    # Check that we have the expected order edges between the results
    hugr = compiled.module
    [a] = find_ext_nodes(hugr, RESULT_EXTENSION.get_op("result_bool").qualified_name())
    [b] = find_ext_nodes(hugr, RESULT_EXTENSION.get_op("result_int").qualified_name())
    [p] = find_ext_nodes(hugr, PRELUDE.get_op("panic").qualified_name())
    [e] = find_ext_nodes(hugr, PRELUDE.get_op("exit").qualified_name())
    [c] = find_ext_nodes(hugr, RESULT_EXTENSION.get_op("result_f64").qualified_name())
    check_order(hugr, [a, b, p, e, c])


def test_qalloc_qfree(validate):
    module = GuppyModule("test")
    module.load(qubit, discard, measure)

    @guppy(module)
    def test() -> None:
        q1 = qubit()
        discard(q1)
        q2 = qubit()
        measure(q2)

    compiled = module.compile()
    validate(compiled)

    # Check that we have the expected order edges between the allocations and frees
    hugr = compiled.module
    [a1, a2] = find_ext_nodes(hugr, QUANTUM_EXTENSION.get_op("QAlloc").qualified_name())
    [d1] = find_ext_nodes(hugr, QUANTUM_EXTENSION.get_op("QFree").qualified_name())
    [d2] = find_ext_nodes(
        hugr, QUANTUM_EXTENSION.get_op("MeasureFree").qualified_name()
    )
    check_order(hugr, [a1, d1, a2, d2])


def test_call(validate):
    module = GuppyModule("test")
    module.load(qubit, discard)

    @guppy(module)
    def my_discard(q: qubit @ owned) -> None:
        discard(q)

    @guppy(module)
    def test() -> None:
        q1 = qubit()
        my_discard(q1)
        q2 = qubit()
        f = my_discard
        f(q2)

    compiled = module.compile()
    validate(compiled)

    # Check that we have the expected order edges between the allocations and calls
    hugr = compiled.module
    [a1, a2] = find_ext_nodes(hugr, QUANTUM_EXTENSION.get_op("QAlloc").qualified_name())
    [d1] = [node for node, data in hugr.nodes() if isinstance(data.op, ops.Call)]
    [d2] = [
        node for node, data in hugr.nodes() if isinstance(data.op, ops.CallIndirect)
    ]
    check_order(hugr, [a1, d1, a2, d2])


def test_nested(validate):
    module = GuppyModule("test")
    module.load(qubit, discard, measure)

    @guppy(module)
    def test() -> None:
        qs1 = array(qubit() for _ in range(10))
        array(measure(q) for q in qs1)
        qs2 = array(qubit() for _ in range(10))
        array(discard(q) for q in qs2)

    compiled = module.compile()
    validate(compiled)

    # Check that we have the expected order edges between the comprehension tail loops
    hugr = compiled.module
    [l1, l2, l3, l4] = [
        node for node, data in hugr.nodes() if isinstance(data.op, ops.TailLoop)
    ]
    check_order(hugr, [l1, l2, l3, l4])
