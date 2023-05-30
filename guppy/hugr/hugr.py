import itertools
import networkx  # type: ignore

from abc import ABC
from contextlib import contextmanager
from typing import Optional, Iterator, Tuple, Any, Callable, Union, Sequence
from dataclasses import dataclass, field

import guppy.hugr.ops as ops
import guppy.hugr.tys as tys
import guppy.hugr.raw as raw
from guppy.guppy_types import GuppyType, type_from_python_value, TupleType, FunctionType, SumType


NodeIdx = int
PortOffset = int


@dataclass()
class Port(ABC):
    """ Base class for ports on nodes. """
    node: "Node"
    offset: PortOffset
    ty: Optional[GuppyType]


class InPort(Port):
    """ Port that incoming wires connect to.  """
    pass


class OutPort(Port):
    """ Port that outgoing wires come from. """
    pass


Edge = tuple[OutPort, InPort]


@dataclass()
class Node:
    """ A node in the graph with a number of input and output ports. """
    idx: NodeIdx
    op: ops.OpType
    in_port_types: list[Optional[GuppyType]]
    out_port_types: list[Optional[GuppyType]]
    parent: "Node"
    meta_data: dict[str, Any] = field(default_factory=dict)

    @property
    def num_in_ports(self) -> int:
        """ The number of input ports on this node. """
        return len(self.in_port_types)

    @property
    def num_out_ports(self) -> int:
        """ The number of output ports on this node. """
        return len(self.out_port_types)

    def add_in_port(self, ty: Optional[GuppyType]) -> InPort:
        """ Adds an input port at the end of the node and returns the port. """
        p = InPort(self, self.num_in_ports, ty)
        self.in_port_types.append(ty)
        return p

    def add_out_port(self, ty: Optional[GuppyType]) -> OutPort:
        """ Adds an output port at the end of the node and returns the port. """
        p = OutPort(self, self.num_out_ports, ty)
        self.out_port_types.append(ty)
        return p

    def in_port(self, offset: PortOffset) -> InPort:
        """ Returns the input port at the given offset. """
        assert offset < self.num_in_ports
        return InPort(self, offset, self.in_port_types[offset])

    def out_port(self, offset: PortOffset) -> OutPort:
        """ Returns the output port at the given offset. """
        assert offset < self.num_out_ports
        return OutPort(self, offset, self.out_port_types[offset])

    def update_op(self) -> None:
        """ Updates the operation associated with this node with type information.

        Feeds type information from the in- and out-ports to the operation class to
        update signature information. This function must be called before serialisation.
        """
        in_types = [t.to_hugr() if t is not None else None for t in self.in_port_types]
        out_types = [t.to_hugr() if t is not None else None for t in self.out_port_types]
        self.op.insert_port_types(in_types, out_types)


class DataflowContainingNode(Node):
    """ A node whose children form a dataflow graph.

    Compared to a normal node, this node tracks the `Input` and `Output` nodes of
    its child DFG which is required to compute the operation signature.
    """
    input_child: Optional[Node] = None  # Input Node for the child dataflow graph
    output_child: Optional[Node] = None  # Output Node for the child dataflow graph

    def update_op(self) -> None:
        """ Updates the operation associated with this node with type information.

        Feeds type information from the in- and out-ports as well as the signature of
        the contained dataflow graph to the operation class to. This function must be
        called before serialisation.
        """
        super().update_op()
        assert self.input_child is not None and self.output_child is not None
        # Input and output node may have extra order edges connected, so we filter Nones here
        ins = [ty.to_hugr() for ty in self.input_child.out_port_types if ty is not None]
        outs = [ty.to_hugr() for ty in self.output_child.in_port_types if ty is not None]
        self.op.insert_child_dfg_signature(inputs=ins, outputs=outs)


TypeList = Sequence[Optional[GuppyType]]


class Hugr:
    """ Hierarchical unified graph representation. """
    name: str
    root: Optional[Node]  # Non-module Hugrs may not have a root
    _graph: networkx.MultiDiGraph  # TODO: We probably don't need networkx.
    _children: dict[NodeIdx, list[Node]]
    _default_parent: Optional[Node]

    def __init__(self, name: Optional[str] = None) -> None:
        """ Creates a new Hugr. """
        self.name = name or "Unnamed"
        self.root = None
        self._graph = networkx.MultiDiGraph()
        self._children = {-1: []}
        self._default_parent = None

    @contextmanager
    def parent(self, parent: Node) -> Iterator[None]:
        """ Context manager to set a default parent for adding new nodes. """
        old_default = self._default_parent
        self._default_parent = parent
        yield
        self._default_parent = old_default

    def _connect_node(self, node: Node, parent: Node, inputs: Optional[list[OutPort]]) -> None:
        self._graph.add_node(node.idx, data=node)
        self._children[node.idx] = []
        self._children[parent.idx if parent else -1].append(node)
        if inputs is not None:
            for i, port in enumerate(inputs):
                self.add_edge(port, node.in_port(i))

    def _add_node(self, op: ops.OpType, input_types: Optional[TypeList] = None, output_types: Optional[TypeList] = None,
                  parent: Optional[Node] = None, inputs: Optional[list[OutPort]] = None,
                  meta_data: Optional[dict[str, Any]] = None) -> Node:
        input_types = input_types or []
        output_types = output_types or []
        parent = parent or self._default_parent
        if parent is None:
            raise ValueError("Parent or default parent must be set!")
        node = Node(idx=self._graph.number_of_nodes(),
                    op=op,
                    in_port_types=[p.ty for p in inputs] if inputs is not None else list(input_types),
                    out_port_types=list(output_types),
                    parent=parent,
                    meta_data=meta_data or {})
        self._connect_node(node, parent, inputs)
        return node

    def _add_dfg_node(self, op: ops.OpType, input_types: Optional[TypeList] = None, output_types: Optional[TypeList] = None,
                      parent: Optional[Node] = None, inputs: Optional[list[OutPort]] = None,
                      meta_data: Optional[dict[str, Any]] = None) -> DataflowContainingNode:
        input_types = input_types or []
        output_types = output_types or []
        parent = parent or self._default_parent
        if parent is None:
            raise ValueError("Parent or default parent must be set!")
        node = DataflowContainingNode(idx=self._graph.number_of_nodes(),
                                      op=op,
                                      in_port_types=[p.ty for p in inputs] if inputs is not None else list(input_types),
                                      out_port_types=list(output_types),
                                      parent=parent,
                                      meta_data=meta_data or {})
        self._connect_node(node, parent, inputs)
        return node

    def add_root(self, name: str) -> Node:
        """ Adds a Root node to the graph.

        Note that each Hugr may only have a single root.
        """
        if self.root is not None:
            raise ValueError("Hugr already has a root node")
        root = self._add_node(op=ops.Module(op=ops.Root()), meta_data={"name": name})
        root.parent = root
        self.root = root
        return root

    def add_constant(self, value: object, parent: Optional[Node] = None) -> Node:
        """ Adds a constant node holding a given value to the graph. """
        # TODO Update this once we have a better constant spec
        # For now, we just create an external function call
        return self._add_node(ops.DummyOp(name=f'Constant: {value}'), [], [type_from_python_value(value)], parent, None)

    def add_arith(self, name: str, args: list[OutPort], out_ty: GuppyType, parent: Optional[Node] = None) -> Node:
        """ Adds a node for an arithmetic operation. """
        # TODO Work with arithmetic resource
        return self._add_node(ops.DummyOp(name=name), None, [out_ty], parent, args)

    def add_input(self, output_tys: Optional[TypeList] = None, parent: Optional[Node] = None) -> Node:
        """ Adds an `Input` node to the graph. """
        parent = parent or self._default_parent
        node = self._add_node(ops.Dataflow(op=ops.Input()), [], output_tys, parent)
        if isinstance(parent, DataflowContainingNode):
            parent.input_child = node
        return node

    def add_output(self, inputs: Optional[list[OutPort]] = None, input_tys: Optional[TypeList] = None,
                   parent: Optional[Node] = None) -> Node:
        """ Adds an `Output` node to the graph. """
        node = self._add_node(ops.Dataflow(op=ops.Output()), input_tys, [], parent, inputs)
        if isinstance(parent, DataflowContainingNode):
            parent.output_child = node
        return node

    def add_block(self, parent: Node) -> DataflowContainingNode:
        """ Adds a `Block` node to the graph. """
        return self._add_dfg_node(ops.BasicBlock(op=ops.Block()), [], [], parent)

    def add_exit(self, output_tys: list[GuppyType], parent: Node) -> Node:
        """ Adds an `Exit` node to the graph. """
        outputs = tys.TypeRow(types=[ty.to_hugr() for ty in output_tys])
        return self._add_node(ops.BasicBlock(op=ops.Exit(cfg_outputs=outputs)), [], [], parent)

    def add_dfg(self, parent: Node) -> DataflowContainingNode:
        """ Adds a nested dataflow `DFG` node to the graph. """
        return self._add_dfg_node(ops.Dataflow(op=ops.DFG()), [], [], parent)

    def add_case(self, parent: Node) -> DataflowContainingNode:
        """ Adds a `Case` node to the graph. """
        return self._add_dfg_node(ops.Case(op=ops.CaseOp()), [], [], parent)

    def add_cfg(self, parent: Node, inputs: list[OutPort]) -> Node:
        """ Adds a nested control-flow `CFG` node to the graph. """
        return self._add_node(ops.Dataflow(op=ops.ControlFlow(op=ops.CFG())), [], [], parent, inputs)

    def add_conditional(self, cond_input: OutPort, inputs: list[OutPort], parent: Optional[Node] = None) -> Node:
        """ Adds a `Conditional` node to the graph. """
        inputs = [cond_input] + inputs
        return self._add_node(ops.Dataflow(op=ops.ControlFlow(op=ops.Conditional())), None, None, parent, inputs)

    def add_tail_loop(self, inputs: list[OutPort], parent: Optional[Node] = None) -> DataflowContainingNode:
        """ Adds a `TailLoop` node to the graph. """
        return self._add_dfg_node(ops.Dataflow(op=ops.ControlFlow(op=ops.TailLoop())), None, None, parent, inputs)

    def add_make_tuple(self, inputs: list[OutPort], parent: Optional[Node] = None) -> Node:
        """ Adds a `MakeTuple` node to the graph. """
        elems: list[GuppyType] = []
        for port in inputs:
            assert port.ty is not None
            elems.append(port.ty)
        ty = TupleType(elems)
        return self._add_node(ops.Dataflow(op=ops.Leaf(op=ops.MakeTuple())), None, [ty], parent, inputs)

    def add_unpack_tuple(self, input_tuple: OutPort, parent: Optional[Node] = None) -> Node:
        """ Adds an `UnpackTuple` node to the graph. """
        assert isinstance(input_tuple.ty, TupleType)
        return self._add_node(ops.Dataflow(op=ops.Leaf(op=ops.UnpackTuple())), None, input_tuple.ty.element_types,
                              parent, [input_tuple])

    def add_tag(self, variants: list[GuppyType], tag: int, inp: OutPort, parent: Optional[Node] = None) -> Node:
        """ Adds a `Tag` node to the graph. """
        types = tys.TypeRow(types=[ty.to_hugr() for ty in variants])
        assert inp.ty == variants[tag]
        return self._add_node(ops.Dataflow(op=ops.Leaf(op=ops.Tag(tag=tag, variants=types))), None,
                              [SumType(variants)], parent, [inp])

    def add_call(self, def_port: OutPort, args: list[OutPort], parent: Optional[Node] = None) -> Node:
        """ Adds a `Call` node to the graph. """
        assert isinstance(def_port.ty, FunctionType)
        return self._add_node(ops.Dataflow(op=ops.Call()), None, def_port.ty.returns, parent, args + [def_port])

    def add_indirect_call(self, def_port: OutPort, args: list[OutPort], parent: Optional[Node] = None) -> Node:
        """ Adds an `IndirectCall` node to the graph. """
        assert isinstance(def_port.ty, FunctionType)
        return self._add_node(ops.Dataflow(op=ops.CallIndirect()), None, def_port.ty.returns, parent, args + [def_port])

    def add_def(self, fun_ty: FunctionType, parent: Node, name: str) -> Node:
        """ Adds a `Def` node to the graph. """
        return self._add_dfg_node(ops.Module(op=ops.Def()), [], [fun_ty], parent, None, meta_data={"name": name})

    def add_declare(self, fun_ty: FunctionType, parent: Node, name: str) -> Node:
        """ Adds a `Declare` node to the graph. """
        return self._add_node(ops.Module(op=ops.Declare()), [], [fun_ty], parent, None, meta_data={"name": name})

    def add_edge(self, src_port: OutPort, tgt_port: InPort) -> Edge:
        """ Adds an edge between two ports. """
        assert src_port.ty == tgt_port.ty
        self._graph.add_edge(src_port.node.idx, tgt_port.node.idx,
                             key=(src_port.offset, tgt_port.offset))
        return src_port, tgt_port

    def nodes(self) -> Iterator[Node]:
        """ Returns an iterator over all nodes in the graph. """
        return (n["data"] for n in self._graph.nodes.values())

    def get_node(self, idx: int) -> Node:
        """ Returns the node corresponding to given index. """
        return self._graph.nodes[idx]["data"]  # type: ignore

    def children(self, node: Node) -> list[Node]:
        """ Returns list of a node's immediate children in the hierarchy. """
        return self._children[node.idx]

    def top_level_nodes(self) -> list[Node]:
        """ Returns list of nodes at the top level of the hierarchy.

        These are nodes that do not have a parent. Usually this will just
        be the `Root` node.
        """
        return self._children[-1]

    def edges(self) -> Iterator[Edge]:
        """ Returns an iterator over all edges in the graph. """
        return (self._to_edge(*e) for e in self._graph.edges(data=True, keys=True))

    def in_edges(self, port: InPort) -> Iterator[Edge]:
        """ Returns an iterator over all edges connected to a given in-port. """
        for e in self._graph.in_edges(port.node.idx, keys=True, data=True):
            src, tgt = self._to_edge(*e)
            if tgt.offset == port.offset:
                yield src, tgt

    def out_edges(self, port: OutPort) -> Iterator[Edge]:
        """ Returns an iterator over all edges originating from a given out-port. """
        for e in self._graph.out_edges(port.node.idx, keys=True, data=True):
            src, tgt = self._to_edge(*e)
            if src.offset == port.offset:
                yield src, tgt

    def _to_edge(self, src: int, tgt: int, key: Tuple[int, int], _data: dict[str, Any]) -> Edge:
        src_node = self.get_node(src)
        tgt_node = self.get_node(tgt)
        return src_node.out_port(key[0]), tgt_node.in_port(key[1])

    def remove_edge(self, src_port: OutPort, tgt_port: InPort) -> None:
        """ Removes an edge from the graph. """
        self._graph.remove_edge(src_port.node.idx, tgt_port.node.idx, key=(src_port.offset, tgt_port.offset))

    def remove_dummy_nodes(self) -> "Hugr":
        """ Replaces dummy ops with external function calls. """
        if self.root is None:
            raise ValueError("Dummy node removal requires a module root node")
        for n in list(self.nodes()):
            if isinstance(n.op, ops.DummyOp):
                name = n.op.name
                fun_ty = FunctionType(list(*n.in_port_types), list(*n.out_port_types))
                decl = self.add_declare(fun_ty.clone(), self.root, name)
                n.op = ops.Dataflow(op=ops.Call())
                self.add_edge(decl.out_port(0), n.add_in_port(fun_ty.clone()))
        return self

    def insert_copies(self) -> "Hugr":
        """ Adds explicit copy/discard nodes to the graph to make ports linear. """
        for n in list(self.nodes()):
            if isinstance(n.op, ops.Dataflow):
                for i, ty in enumerate(n.out_port_types):
                    if ty is not None:
                        port = n.out_port(i)
                        edges = list(self.out_edges(port))
                        if len(edges) != 1:
                            hugr_ty = ty.to_hugr()
                            assert isinstance(hugr_ty, tys.Classic)
                            copy_op = ops.Dataflow(op=ops.Leaf(op=ops.Copy(n_copies=len(edges), typ=hugr_ty.ty)))
                            copy_node = self._add_node(copy_op, inputs=[port], parent=n.parent)
                            for src, tgt in edges:
                                self.remove_edge(src, tgt)
                                self.add_edge(copy_node.add_out_port(ty), tgt)
        return self

    def insert_order_edges(self) -> "Hugr":
        """ Adds state edges to all dataflow ops without inputs outputs.

        We add state edges connecting them to the input or output node of the DFG.
        This action must be performed before serialisation.
        """
        for n in self.nodes():
            if isinstance(n.op, ops.Dataflow):
                assert isinstance(n.parent, DataflowContainingNode)
                if n.num_in_ports == 0 and not isinstance(n.op.op, ops.Input):
                    assert n.parent.input_child is not None
                    src = n.parent.input_child.add_out_port(None)
                    tgt = n.add_in_port(None)
                    self.add_edge(src, tgt)
                if n.num_out_ports == 0 and not isinstance(n.op.op, ops.Output):
                    assert n.parent.output_child is not None
                    src = n.add_out_port(None)
                    tgt = n.parent.output_child.add_in_port(None)
                    self.add_edge(src, tgt)
                # Special case: Call ops for functions without any arguments are
                # only connected to the top-level def/declare and also need an
                # order edge
                if isinstance(n.op.op, ops.Call) and n.num_in_ports == 1:
                    assert n.parent.input_child is not None
                    src = n.parent.input_child.add_out_port(None)
                    tgt = n.add_in_port(None)
                    self.add_edge(src, tgt)
        return self

    def to_raw(self) -> raw.RawHugr:
        """ Returns the raw representation of this HUGR for serialisation. """
        self.remove_dummy_nodes()
        self.insert_copies()
        self.insert_order_edges()
        # Hugr requires that Input/Output nodes are the first/last children in
        # a DFG. Furthermore, exit nodes must be the last children of CFGs. We're
        # going to satisfy this trivially by first serialising all inputs and
        # serialising outputs and exists at the very end
        input_nodes: list[Node] = []
        output_nodes: list[Node] = []
        entry_nodes: list[Node] = []
        exit_nodes: list[Node] = []
        remaining_nodes: list[Node] = []
        indices = itertools.count(start=1)  # Hugr indices start from 1
        raw_index: dict[int, raw.NodeID] = {}
        for n in self.nodes():
            if isinstance(n.op, ops.Dataflow) and isinstance(n.op.op, ops.Input):
                input_nodes.append(n)
            elif isinstance(n.op, ops.Dataflow) and isinstance(n.op.op, ops.Output):
                output_nodes.append(n)
            elif isinstance(n.op, ops.BasicBlock) and isinstance(n.op.op, ops.Block) and n.num_in_ports == 0:
                entry_nodes.append(n)
            elif isinstance(n.op, ops.BasicBlock) and isinstance(n.op.op, ops.Exit):
                exit_nodes.append(n)
            else:
                remaining_nodes.append(n)
        for n in itertools.chain(iter(entry_nodes), iter(input_nodes), iter(remaining_nodes), iter(output_nodes),
                                 iter(exit_nodes)):
            raw_index[n.idx] = next(indices)

        nodes: list[Optional[raw.Node]] = [None] * self._graph.number_of_nodes()
        op_types: dict[int, ops.OpType] = {}
        for n in self.nodes():
            # Ports for constE edges are only present if they are connected
            is_const = not isinstance(n.op, ops.Dataflow) and n.num_out_ports == 1 and n.out_port_types[0] is not None
            num_out_ports = 0 if is_const and next(self.out_edges(n.out_port(0)), None) is None else n.num_out_ports
            idx = raw_index[n.idx]
            nodes[idx - 1] = (raw_index[n.parent.idx], n.num_in_ports, num_out_ports)
            n.update_op()
            op_types[idx] = n.op

        edges: list[raw.Edge] = []
        for src, tgt in self.edges():
            edges.append(((raw_index[src.node.idx], src.offset), (raw_index[tgt.node.idx], tgt.offset)))

        if self.root is None:
            raise ValueError("Raw Hugr requires a root node")

        return raw.RawHugr(nodes=nodes, edges=edges, root=raw_index[self.root.idx], op_types=op_types)
