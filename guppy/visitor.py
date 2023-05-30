""" AST visitor based on ast.NodeVisitor that can pass extra arguments to visit(...). """

import ast
from typing import Any


class AstVisitor(object):
    """
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
    def visit(self, node: Any, *args: Any, **kwargs: Any) -> Any:
        """Visit a node."""
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node, *args, **kwargs)

    def generic_visit(self, node: Any, *args: Any, **kwargs: Any) -> Any:
        """Called if no explicit visitor function exists for a node."""
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        self.visit(item, *args, **kwargs)
            elif isinstance(value, ast.AST):
                self.visit(value, *args, **kwargs)


def name_nodes_in_expr(expr: ast.expr) -> list[ast.Name]:
    """ Returns a list of all `Name` nodes occurring in an expression. """
    class Visitor(AstVisitor):
        names: list[ast.Name]

        def __init__(self) -> None:
            self.names = []

        def visit_Name(self, node: ast.Name) -> None:
            self.names.append(node)

    v = Visitor()
    v.visit(expr)
    return v.names
