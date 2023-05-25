import networkx
from typing import Optional, Iterator, Tuple, Any
from enum import IntEnum
from dataclasses import dataclass, field

from guppy.guppy_types import GuppyType, type_from_python_value


@dataclass()
class Port:
    node: "Node"
    offset: int
    ty: Optional[GuppyType]


class InPort(Port):
    pass


class OutPort(Port):
    pass


TypeList = list[Optional[GuppyType]]


@dataclass()
class Node:
    idx: int
    parent: "Node"
    name: str
    meta_data: dict[str, Any]
    in_port_types: TypeList
    out_port_types: TypeList

    @property
    def num_in_ports(self):
        return len(self.in_port_types)

    @property
    def num_out_ports(self):
        return len(self.out_port_types)

    def add_in_port(self, ty: Optional[GuppyType]) -> InPort:
        p = InPort(self, self.num_in_ports, ty)
        self.in_port_types.append(ty)
        return p

    def add_out_port(self, ty: Optional[GuppyType]) -> OutPort:
        p = OutPort(self, self.num_out_ports, ty)
        self.out_port_types.append(ty)
        return p

    def in_port(self, idx: int) -> InPort:
        assert idx < self.num_in_ports
        return InPort(self, idx, self.in_port_types[idx])

    def out_port(self, idx: int) -> OutPort:
        assert idx < self.num_out_ports
        return OutPort(self, idx, self.out_port_types[idx])


@dataclass(frozen=True)
class Edge:
    src_port: OutPort
    target_port: InPort


class Hugr:
    def __init__(self, name: str = None) -> None:
        self.name = name
        self._graph = networkx.MultiDiGraph()
        self.default_parent = None
        self._children = {-1: []}

    def add_node(self, name: str, inputs: Optional[TypeList] = None, outputs: Optional[TypeList] = None,
                 parent: Optional[Node] = None, args: Optional[list[OutPort]] = None,
                 meta_data: Optional[dict[str, Any]] = None) -> Node:
        inputs = inputs or []
        outputs = outputs or []
        parent = parent or self.default_parent
        node = Node(idx=self._graph.number_of_nodes(),
                    in_port_types=[p.ty for p in args] if args is not None else inputs,
                    out_port_types=outputs,
                    parent=parent,
                    name=name,
                    meta_data=meta_data or {})
        self._graph.add_node(node.idx, data=node)
        self._children[node.idx] = []
        self._children[parent.idx if parent else -1].append(node)
        if args is not None:
            for i, port in enumerate(args):
                self.add_edge(port, node.in_port(i))
        return node

    def add_constant_node(self, value: object, parent: Optional[Node] = None) -> Node:
        return self.add_node("constant", [], [type_from_python_value(value)], parent, meta_data={"value": value})

    def add_input_node(self, outputs: Optional[TypeList] = None, parent: Optional[Node] = None) -> Node:
        return self.add_node("input", [], outputs, parent)

    def add_output_node(self, inputs: Optional[TypeList] = None, parent: Optional[Node] = None,
                        args: Optional[list[OutPort]] = None) -> Node:
        return self.add_node("output", inputs, [], parent, args)

    def add_beta_node(self, parent: Node) -> Node:
        return self.add_node("beta", [], [], parent)

    def add_delta_node(self, parent: Node) -> Node:
        return self.add_node("delta", [], [], parent)

    def add_kappa_node(self, parent: Node) -> Node:
        return self.add_node("kappa", [], [], parent)

    def add_edge(self, src_port: OutPort, tgt_port: InPort) -> Edge:
        assert src_port.ty == tgt_port.ty
        self._graph.add_edge(src_port.node.idx, tgt_port.node.idx,
                             key=(src_port.offset, tgt_port.offset))
        return Edge(src_port, tgt_port)

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

    def _to_edge(self, src: int, tgt: int, key: Tuple[int, int], data: dict[str, Any]) -> Edge:
        src = self.get_node(src)
        tgt = self.get_node(tgt)
        return Edge(src.out_port(key[0]), tgt.in_port(key[1]))

