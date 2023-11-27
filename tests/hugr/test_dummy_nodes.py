from guppy.gtypes import FunctionType, BoolType, TupleType
from guppy.hugr import ops
from guppy.hugr.hugr import Hugr


def test_single_dummy():
    g = Hugr()
    defn = g.add_def(FunctionType([BoolType()], BoolType()), g.root, "test")
    dfg = g.add_dfg(defn)
    inp = g.add_input([BoolType()], dfg).out_port(0)
    dummy = g.add_node(
        ops.DummyOp(name="dummy"), inputs=[inp], output_types=[BoolType()], parent=dfg
    )
    g.add_output([dummy.out_port(0)], parent=dfg)

    g.remove_dummy_nodes()
    [decl] = [n for n in g.nodes() if isinstance(n.op, ops.FuncDecl)]
    assert decl.op.name == "dummy"


def test_unique_names():
    g = Hugr()
    defn = g.add_def(FunctionType([BoolType()], TupleType([BoolType(), BoolType()])), g.root, "test")
    dfg = g.add_dfg(defn)
    inp = g.add_input([BoolType()], dfg).out_port(0)
    dummy1 = g.add_node(
        ops.DummyOp(name="dummy"), inputs=[inp], output_types=[BoolType()], parent=dfg
    )
    dummy2 = g.add_node(
        ops.DummyOp(name="dummy"), inputs=[inp], output_types=[BoolType()], parent=dfg
    )
    g.add_output([dummy1.out_port(0), dummy2.out_port(0)], parent=dfg)

    g.remove_dummy_nodes()
    [decl1, decl2] = [n for n in g.nodes() if isinstance(n.op, ops.FuncDecl)]
    assert {decl1.op.name, decl2.op.name} == {"dummy", "dummy$1"}

