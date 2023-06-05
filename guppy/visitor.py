""" AST visitor based on ast.NodeVisitor that can pass extra arguments to visit(...). """

import ast
from functools import singledispatch
from typing import Any, TypeVar, Generic

T = TypeVar("T")


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

    @singledispatch
    def visit(self, node: Any, *args: Any, **kwargs: Any) -> T:
        """Visit a node."""
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node, *args, **kwargs)

    def generic_visit(self, node: Any, *args: Any, **kwargs: Any) -> T:
        """Called if no explicit visitor function exists for a node."""
        raise NotImplementedError(f"visit_{node.__class__.__name__} is not implemented")


def name_nodes_in_expr(expr: ast.expr) -> list[ast.Name]:
    """ Returns a list of all `Name` nodes occurring in an expression. """
    class Visitor(AstVisitor[None]):
        names: list[ast.Name]

        def __init__(self) -> None:
            self.names = []

        def visit_Name(self, node: ast.Name) -> None:
            self.names.append(node)

        def generic_visit(self, node: Any, *args: Any, **kwargs: Any) -> None:
            pass

    v = Visitor()
    v.visit(expr)
    return v.names
