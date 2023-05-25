import itertools
from abc import ABC

import networkx
from typing import Optional, Iterator, Tuple, Any, Callable, Union
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
    def num_in_ports(self):
        """ The number of input ports on this node. """
        return len(self.in_port_types)

    @property
    def num_out_ports(self):
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

    def update_op(self):
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

    def update_op(self):
        """ Updates the operation associated with this node with type information.

        Feeds type information from the in- and out-ports as well as the signature of
        the contained dataflow graph to the operation class to. This function must be
        called before serialisation.
        """
        super().update_op()
        # Input and output node may have extra order edges connected, so we filter Nones here
        ins = [ty.to_hugr() for ty in self.input_child.out_port_types if ty is not None]
        outs = [ty.to_hugr() for ty in self.output_child.in_port_types if ty is not None]
        self.op.insert_child_dfg_signature(inputs=ins, outputs=outs)


TypeList = list[Optional[GuppyType]]


class Hugr:
    """ Hierarchical unified graph representation. """
    def __init__(self, name: str = None) -> None:
        self.name = name
        self._graph = networkx.MultiDiGraph()
        self.default_parent = None
        self._children = {-1: []}
        self.root: Optional[Node] = None

    def add_node(self, op: ops.OpType, inputs: Optional[TypeList] = None, outputs: Optional[TypeList] = None,
                 parent: Optional[Node] = None, args: Optional[list[OutPort]] = None,
                 meta_data: Optional[dict[str, Any]] = None, node_class: Callable = Node) \
            -> Union[Node, DataflowContainingNode]:
        inputs = inputs or []
        outputs = outputs or []
        parent = parent or self.default_parent
        node = node_class(idx=self._graph.number_of_nodes(),
                          op=op,
                          in_port_types=[p.ty for p in args] if args is not None else inputs,
                          out_port_types=outputs,
                          parent=parent,
                          meta_data=meta_data or {})
        self._graph.add_node(node.idx, data=node)
        self._children[node.idx] = []
        self._children[parent.idx if parent else -1].append(node)
        if args is not None:
            for i, port in enumerate(args):
                self.add_edge(port, node.in_port(i))
        return node

    def add_root(self, name: str) -> Node:
        if self.root is not None:
            raise ValueError("Hugr already has a root node")
        root = self.add_node(op=ops.Module(op=ops.Root()), meta_data={"name": name})
        root.parent = root
        self.root = root
        return root

    def add_constant_node(self, value: object, parent: Optional[Node] = None) -> Node:
        # TODO Update this once we have a better constant spec
        # For now, we just create an external function call§
        ext_decl = self.add_declare_node(FunctionType([], [type_from_python_value(value)]), self.root, f'"{value}"')
        return self.add_call_node(ext_decl.out_port(0), [], parent)

    def add_arith_node(self, name: str, args: list[OutPort], outputs: TypeList, parent: Optional[Node] = None) -> Node:
        # TODO Work with arithmetic resource
        # For now, we just create an external function call
        ext_decl = self.add_declare_node(FunctionType([p.ty for p in args], outputs), self.root, name)
        return self.add_call_node(ext_decl.out_port(0), args, parent)

    def add_input_node(self, outputs: Optional[TypeList] = None, parent: Optional[Node] = None) -> Node:
        parent = parent or self.default_parent
        node = self.add_node(ops.Dataflow(op=ops.Input()), [], outputs, parent)
        if isinstance(parent, DataflowContainingNode):
            parent.input_child = node
        return node

    def add_output_node(self, inputs: Optional[TypeList] = None, parent: Optional[Node] = None,
                        args: Optional[list[OutPort]] = None) -> Node:
        node = self.add_node(ops.Dataflow(op=ops.Output()), inputs, [], parent, args)
        if isinstance(parent, DataflowContainingNode):
            parent.output_child = node
        return node

    def add_beta_node(self, parent: Node) -> DataflowContainingNode:
        return self.add_node(ops.BasicBlock(op=ops.Block()), [], [], parent, node_class=DataflowContainingNode)

    def add_exit_node(self, output_types: list[GuppyType], parent: Node) -> Node:
        outputs = tys.TypeRow(types=[ty.to_hugr() for ty in output_types])
        return self.add_node(ops.BasicBlock(op=ops.Exit(cfg_outputs=outputs)), [], [], parent)

    def add_delta_node(self, parent: Node) -> Node:
        return self.add_node(ops.Dataflow(op=ops.DFG()), [], [], parent, node_class=DataflowContainingNode)

    def add_case_node(self, parent: Node) -> Node:
        return self.add_node(ops.Case(op=ops.CaseOp()), [], [], parent, node_class=DataflowContainingNode)

    def add_kappa_node(self, parent: Node, args: Optional[list[OutPort]] = None) -> Node:
        return self.add_node(ops.Dataflow(op=ops.ControlFlow(op=ops.CFG())), [], [], parent, args)

    def add_gamma_node(self, cond_arg: OutPort, args: list[OutPort], outputs: Optional[TypeList] = None,
                       parent: Optional[Node] = None) -> Node:
        args = [cond_arg] + args
        return self.add_node(ops.Dataflow(op=ops.ControlFlow(op=ops.Conditional())), None, outputs, parent, args)

    def add_theta_node(self, args: list[OutPort], outputs: Optional[TypeList] = None,
                       parent: Optional[Node] = None) -> Node:
        return self.add_node(ops.Dataflow(op=ops.ControlFlow(op=ops.TailLoop())), None, outputs, parent, args,
                             node_class=DataflowContainingNode)

    def add_make_tuple_node(self, args: list[OutPort], parent: Optional[Node] = None) -> Node:
        ty = TupleType([a.ty for a in args])
        return self.add_node(ops.Dataflow(op=ops.Leaf(op=ops.MakeTuple())), None, [ty], parent, args)

    def add_unpack_tuple_node(self, arg: OutPort, parent: Optional[Node] = None) -> Node:
        assert isinstance(arg.ty, TupleType)
        return self.add_node(ops.Dataflow(op=ops.Leaf(op=ops.UnpackTuple())), None, arg.ty.element_types, parent, [arg])

    def add_tag_node(self, variants: list[GuppyType], tag: int, arg: OutPort, parent: Optional[Node] = None) -> Node:
        types = tys.TypeRow(types=[ty.to_hugr() for ty in variants])
        assert arg.ty == variants[tag]
        return self.add_node(ops.Dataflow(op=ops.Leaf(op=ops.Tag(tag=tag, variants=types))), None,
                             [SumType(variants)], parent, [arg])

    def add_call_node(self, def_port: OutPort, args: list[OutPort], parent: Optional[Node] = None) -> Node:
        assert isinstance(def_port.ty, FunctionType)
        return self.add_node(ops.Dataflow(op=ops.Call()), None, def_port.ty.returns, parent, args + [def_port])

    def add_indirect_call_node(self, def_port: OutPort, args: list[OutPort], parent: Optional[Node] = None) -> Node:
        assert isinstance(def_port.ty, FunctionType)
        return self.add_node(ops.Dataflow(op=ops.CallIndirect()), None, def_port.ty.returns, parent, args + [def_port])

    def add_def_node(self, fun_ty: FunctionType, parent: Node, name: str) -> Node:
        return self.add_node(ops.Module(op=ops.Def()), [], [fun_ty], parent, None, meta_data={"name": name},
                             node_class=DataflowContainingNode)

    def add_declare_node(self, fun_ty: FunctionType, parent: Node, name: str) -> Node:
        return self.add_node(ops.Module(op=ops.Declare()), [], [fun_ty], parent, None, meta_data={"name": name})

    def add_edge(self, src_port: OutPort, tgt_port: InPort) -> Edge:
        assert src_port.ty == tgt_port.ty
        self._graph.add_edge(src_port.node.idx, tgt_port.node.idx,
                             key=(src_port.offset, tgt_port.offset))
        return src_port, tgt_port

    def nodes(self) -> Iterator[Node]:
        return (n["data"] for n in self._graph.nodes.values())

    def get_node(self, idx: int) -> Node:
        return self._graph.nodes[idx]["data"]

    def children(self, node: Node) -> list[Node]:
        """ Returns list of a node's immediate children in the hierarchy """
        return self._children[node.idx]

    def top_level_nodes(self) -> list[Node]:
        """ Returns list of nodes at the top level of the hierarchy """
        return self._children[-1]

    def edges(self) -> Iterator[Edge]:
        return (self._to_edge(*e) for e in self._graph.edges(data=True, keys=True))

    def in_edges(self, port: InPort) -> Iterator[Edge]:
        for e in self._graph.in_edges(port.node.idx, keys=True, data=True):
            src, tgt = self._to_edge(*e)
            if tgt.offset == port.offset:
                yield src, tgt

    def out_edges(self, port: OutPort) -> Iterator[Edge]:
        for e in self._graph.out_edges(port.node.idx, keys=True, data=True):
            src, tgt = self._to_edge(*e)
            if src.offset == port.offset:
                yield src, tgt

    def _to_edge(self, src: int, tgt: int, key: Tuple[int, int], _data: dict[str, Any]) -> Edge:
        src = self.get_node(src)
        tgt = self.get_node(tgt)
        return src.out_port(key[0]), tgt.in_port(key[1])

    def remove_edge(self, src_port: OutPort, tgt_port: InPort) -> None:
        self._graph.remove_edge(src_port.node.idx, tgt_port.node.idx, key=(src_port.offset, tgt_port.offset))

    def insert_copies(self) -> "Hugr":
        """ Adds explicit copy/discard nodes to the graph to make ports linear. """
        for n in list(self.nodes()):
            if isinstance(n.op, ops.Dataflow):
                for i, ty in enumerate(n.out_port_types):
                    port = n.out_port(i)
                    edges = list(self.out_edges(port))
                    if len(edges) != 1:
                        hugr_ty = ty.to_hugr()
                        assert isinstance(hugr_ty, tys.Classic)
                        copy_op = ops.Dataflow(op=ops.Leaf(op=ops.Copy(n_copies=len(edges), typ=hugr_ty.ty)))
                        copy_node = self.add_node(copy_op, args=[port], parent=n.parent)
                        for src, tgt in edges:
                            self.remove_edge(src, tgt)
                            self.add_edge(copy_node.add_out_port(ty), tgt)
        return self

    def insert_order_edges(self) -> "Hugr":
        """
        Adds state edges to all dataflow ops without inputs outputs connecting them
        to the input or output node of the DFG.
        """
        for n in self.nodes():
            if isinstance(n.op, ops.Dataflow):
                assert isinstance(n.parent, DataflowContainingNode)
                if n.num_in_ports == 0 and not isinstance(n.op.op, ops.Input):
                    src = n.parent.input_child.add_out_port(None)
                    tgt = n.add_in_port(None)
                    self.add_edge(src, tgt)
                if n.num_out_ports == 0 and not isinstance(n.op.op, ops.Output):
                    src = n.add_out_port(None)
                    tgt = n.parent.output_child.add_in_port(None)
                    self.add_edge(src, tgt)
                # Special case: Call ops for functions without any arguments are
                # only connected to the top-level def/declare and also need an
                # order edge
                if isinstance(n.op.op, ops.Call) and n.num_in_ports == 1:
                    src = n.parent.input_child.add_out_port(None)
                    tgt = n.add_in_port(None)
                    self.add_edge(src, tgt)
        return self

    def to_raw(self) -> raw.RawHugr:
        """ Returns the raw representation of this HUGR for serialisation. """
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

        return raw.RawHugr(nodes=nodes, edges=edges, root=raw_index[self.root.idx], op_types=op_types)
