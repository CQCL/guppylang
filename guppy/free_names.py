import ast
from typing import Any, Optional


class NameVisitor(ast.NodeVisitor):
    names: list[ast.Name]

    def __init__(self) -> None:
        self.names = []

    def visit_Name(self, node: ast.Name) -> None:
        self.names.append(node)


class FreeNameVisitor(ast.NodeVisitor):
    free: dict[str, ast.Name]
    bound: set[str]

    def __init__(self, bound: Optional[set[str]] = None) -> None:
        self.free = {}
        self.bound = bound or set()

    def visit_Name(self, node: ast.Name) -> None:
        if node.id not in self.bound:
            self.free.setdefault(node.id, node)

    def visit_Assign(self, node: ast.Assign) -> None:
        self.visit(node.value)
        self.bound |= set(n.id for t in node.targets for n in name_nodes_in_ast(t))

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self.visit(node.value)
        self.bound |= set(n.id for n in name_nodes_in_ast(node.target))

    def visit_If(self, node: ast.If) -> None:
        self.visit(node.test)
        if_visitor = FreeNameVisitor(self.bound.copy())
        else_visitor = FreeNameVisitor(self.bound.copy())
        for n in node.body:
            if_visitor.visit(n)
        for n in node.orelse or []:
            else_visitor.visit(n)
        self.free |= if_visitor.free | else_visitor.free
        self.bound |= if_visitor.bound & else_visitor.bound

    def visit_While(self, node: ast.While) -> None:
        self.visit(node.test)
        visitor = FreeNameVisitor(self.bound.copy())
        for n in node.body:
            visitor.visit(n)
        self.free |= visitor.free


def name_nodes_in_ast(node: Any) -> list[ast.Name]:
    v = NameVisitor()
    v.visit(node)
    return v.names


def free_names(node: Any, bound: Optional[set[str]] = None) -> dict[str, ast.Name]:
    v = FreeNameVisitor(bound)
    v.visit(node)
    return v.free
