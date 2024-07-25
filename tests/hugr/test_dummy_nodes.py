from hugr.serialization import ops

from guppylang.tys.builtin import bool_type
from guppylang.tys.ty import FunctionType, TupleType, InputFlags, FuncInput
from guppylang.hugr_builder.hugr import Hugr, DummyOp


def test_single_dummy():
    g = Hugr()
    defn = g.add_def(
        FunctionType([FuncInput(bool_type(), InputFlags.NoFlags)], bool_type()),
        g.root,
        "test",
    )
    dfg = g.add_dfg(defn)
    inp = g.add_input([bool_type()], dfg).out_port(0)
    dummy = g.add_node(
        DummyOp("dummy"), inputs=[inp], output_types=[bool_type()], parent=dfg
    )
    g.add_output([dummy.out_port(0)], parent=dfg)

    g.remove_dummy_nodes()
    [decl] = [n for n in g.nodes() if isinstance(n.op.root, ops.FuncDecl)]
    assert decl.op.root.name == "dummy"


def test_unique_names():
    g = Hugr()
    defn = g.add_def(
        FunctionType(
            [FuncInput(bool_type(), InputFlags.NoFlags)],
            TupleType([bool_type(), bool_type()]),
        ),
        g.root,
        "test",
    )
    dfg = g.add_dfg(defn)
    inp = g.add_input([bool_type()], dfg).out_port(0)
    dummy1 = g.add_node(
        DummyOp("dummy"), inputs=[inp], output_types=[bool_type()], parent=dfg
    )
    dummy2 = g.add_node(
        DummyOp("dummy"), inputs=[inp], output_types=[bool_type()], parent=dfg
    )
    g.add_output([dummy1.out_port(0), dummy2.out_port(0)], parent=dfg)

    g.remove_dummy_nodes()
    [decl1, decl2] = [n for n in g.nodes() if isinstance(n.op.root, ops.FuncDecl)]
    assert {decl1.op.root.name, decl2.op.root.name} == {"dummy", "dummy$1"}
