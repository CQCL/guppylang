import ast
from typing import Any, TypeVar, Generic, Union


AstNode = Union[
    ast.AST,
    ast.operator,
    ast.expr,
    ast.arg,
    ast.stmt,
    ast.Name,
    ast.keyword,
    ast.FunctionDef,
]

T = TypeVar("T", covariant=True)


class AstVisitor(Generic[T]):
    """
    Note: This class is based on the implementation of `ast.NodeVisitor` but
    allows extra arguments to be passed to the `visit` functions.

    Original documentation:

    A node visitor base class that walks the abstract syntax tree and calls a
    visitor function for every node found.  This function may return a value
    which is forwarded by the `visit` method.

    This class is meant to be subclassed, with the subclass adding visitor
    methods.

    Per default the visitor functions for the nodes are ``'visit_'`` +
    class name of the node.  So a `TryFinally` node visit function would
    be `visit_TryFinally`.  This behavior can be changed by overriding
    the `visit` method.  If no visitor function exists for a node
    (return value `None`) the `generic_visit` visitor is used instead.

    Don't use the `NodeVisitor` if you want to apply changes to nodes during
    traversing.  For this a special visitor exists (`NodeTransformer`) that
    allows modifications.
    """

    def visit(self, node: Any, *args: Any, **kwargs: Any) -> T:
        """Visit a node."""
        method = "visit_" + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node, *args, **kwargs)

    def generic_visit(self, node: Any, *args: Any, **kwargs: Any) -> T:
        """Called if no explicit visitor function exists for a node."""
        raise NotImplementedError(f"visit_{node.__class__.__name__} is not implemented")


class NameVisitor(ast.NodeVisitor):
    """Visitor to collect all `Name` nodes occurring in an AST."""

    names: list[ast.Name]

    def __init__(self) -> None:
        self.names = []

    def visit_Name(self, node: ast.Name) -> None:
        self.names.append(node)


def name_nodes_in_ast(node: Any) -> list[ast.Name]:
    """Returns all `Name` nodes occurring in an AST."""
    v = NameVisitor()
    v.visit(node)
    return v.names


def line_col(node: ast.AST) -> tuple[int, int]:
    """Returns the line and column of an ast node."""
    return node.lineno, node.col_offset
