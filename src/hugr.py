import networkx
from typing import Optional, Iterator, Tuple, Any
from enum import IntEnum
from dataclasses import dataclass

from guppy_types import GuppyType


@dataclass(frozen=True)
class Port:
    node_idx: int
    offset: int


class InPort(Port):
    pass


class OutPort(Port):
    pass


@dataclass()
class Node:
    idx: int
    parent: "Node"
    name: str
    meta_data: dict[str, Any]
    num_in_ports: int
    num_out_ports: int

    def add_in_port(self) -> InPort:
        p = InPort(self.idx, self.num_in_ports)
        self.num_in_ports += 1
        return p

    def add_out_port(self) -> OutPort:
        p = OutPort(self.idx, self.num_out_ports)
        self.num_out_ports += 1
        return p

    def in_port(self, idx: int) -> InPort:
        assert idx < self.num_in_ports
        return InPort(self.idx, idx)

    def out_port(self, idx: int) -> OutPort:
        assert idx < self.num_out_ports
        return OutPort(self.idx, idx)


class EKind(IntEnum):
    Value = 0
    ConstE = 1
    State = 2
    ControlFlow = 3


@dataclass(frozen=True)
class Edge:
    src_port: OutPort
    target_port: InPort
    kind: EKind
    type: Optional[GuppyType] = None


class Hugr:
    def __init__(self, name: str = None) -> None:
        self.name = name
        self._graph = networkx.MultiDiGraph()
        self.default_parent = None
        self._children = {-1: []}

    def add_node(self, name: str, inputs: int = 0, outputs: int = 0, parent: Optional[Node] = None,
                 args: Optional[list[tuple[OutPort, GuppyType]]] = None, meta_data: Optional[dict[str, Any]] = None) -> Node:
        parent = parent if parent is not None else self.default_parent
        node = Node(idx=self._graph.number_of_nodes(),
                    num_in_ports=len(args) if args is not None else inputs,
                    num_out_ports=outputs,
                    parent=parent,
                    name=name,
                    meta_data=meta_data or {})
        self._graph.add_node(node.idx, data=node)
        self._children[node.idx] = []
        self._children[parent.idx if parent else -1].append(node)
        if args is not None:
            for i, (port, ty) in enumerate(args):
                self.add_edge(port, node.in_port(i), kind=EKind.Value, type=ty)
        return node

    def add_constant_node(self, value: object, parent: Optional[Node] = None) -> Node:
        return self.add_node("constant", 0, 1, parent, meta_data={"value": value})

    def add_input_node(self, outputs: int = 0, parent: Optional[Node] = None) -> Node:
        return self.add_node("input", 0, outputs, parent)

    def add_output_node(self, inputs: int = 0, parent: Optional[Node] = None,
                        args: Optional[list[tuple[OutPort, GuppyType]]] = None) -> Node:
        return self.add_node("output", inputs, 0, parent, args)

    def add_beta_node(self, parent: Node) -> Node:
        return self.add_node("beta", 0, 0, parent)

    def add_delta_node(self, parent: Node) -> Node:
        return self.add_node("delta", 0, 0, parent)

    def add_kappa_node(self, parent: Node) -> Node:
        return self.add_node("kappa", 0, 0, parent)

    def add_edge(self, src_port: OutPort, tgt_port: InPort, kind: EKind, type: Optional["Type"] = None) -> Edge:
        self._graph.add_edge(src_port.node_idx, tgt_port.node_idx,
                             key=(src_port.offset, tgt_port.offset),
                             data=(kind, type))
        return Edge(src_port, tgt_port, kind)

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

    def _to_edge(self, src: int, tgt: int, key: Tuple[int, int], data: dict[str, Tuple[EKind, Optional[GuppyType]]]) -> Edge:
        src = self.get_node(src)
        tgt = self.get_node(tgt)
        data = data["data"]
        return Edge(src.out_port(key[0]), tgt.in_port(key[1]), data[0], data[1])

