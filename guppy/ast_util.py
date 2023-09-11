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


class ReturnVisitor(ast.NodeVisitor):
    """Visitor to collect all `Return` nodes occurring in an AST."""

    returns: list[ast.Return]
    inside_func_def: bool

    def __init__(self) -> None:
        self.returns = []
        self.inside_func_def = False

    def visit_Return(self, node: ast.Return) -> None:
        self.returns.append(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Don't descend into nested function definitions
        if not self.inside_func_def:
            self.inside_func_def = True
            for n in node.body:
                self.visit(n)


def return_nodes_in_ast(node: Any) -> list[ast.Return]:
    """Returns all `Return` nodes occurring in an AST."""
    v = ReturnVisitor()
    v.visit(node)
    return v.returns


def line_col(node: ast.AST) -> tuple[int, int]:
    """Returns the line and column of an ast node."""
    return node.lineno, node.col_offset


def set_location_from(node: ast.AST, loc: ast.AST) -> None:
    """Copy source location from one AST node to the other."""
    node.lineno = loc.lineno
    node.col_offset = loc.col_offset
    node.end_lineno = loc.end_lineno
    node.end_col_offset = loc.end_col_offset


def is_empty_body(func_ast: ast.FunctionDef) -> bool:
    """Returns `True` if the body of a function definition is empty.

    This is the case if the body only contains a single `pass` statement or an ellipsis
    `...` expressions.
    """
    if len(func_ast.body) == 0:
        return True
    if len(func_ast.body) > 1:
        return False
    [n] = func_ast.body
    return isinstance(n, ast.Pass) or (isinstance(n, ast.Expr) and isinstance(n.value, ast.Ellipsis))
