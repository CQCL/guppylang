"""Custom AST nodes used by Guppy"""

import ast
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

from guppylang.gtypes import FunctionType, GuppyType, Inst

if TYPE_CHECKING:
    from guppylang.cfg.cfg import CFG
    from guppylang.checker.cfg_checker import CheckedCFG
    from guppylang.checker.core import CallableVariable, Variable


class LocalName(ast.Name):
    id: str

    _fields = ("id",)


class GlobalName(ast.Name):
    id: str
    value: "Variable"

    _fields = (
        "id",
        "value",
    )


class LocalCall(ast.expr):
    func: ast.expr
    args: list[ast.expr]

    _fields = (
        "func",
        "args",
    )


class GlobalCall(ast.expr):
    func: "CallableVariable"
    args: list[ast.expr]
    type_args: Inst  # Inferred type arguments

    _fields = (
        "func",
        "args",
        "type_args",
    )


class TypeApply(ast.expr):
    value: ast.expr
    tys: Sequence[GuppyType]

    _fields = (
        "value",
        "tys",
    )


class MakeIter(ast.expr):
    """Creates an iterator using the `__iter__` magic method.

    This node is inserted in `for` loops and list comprehensions.
    """

    value: ast.expr

    # Node that triggered the creation of this iterator. For example, a for loop stmt.
    # It is not mentioned in `_fields` so that it is not visible to AST visitors
    origin_node: ast.AST

    _fields = ("value",)


class IterHasNext(ast.expr):
    """Checks if an iterator has a next element using the `__hasnext__` magic method.

    This node is inserted in `for` loops and list comprehensions.
    """

    value: ast.expr

    _fields = ("value",)


class IterNext(ast.expr):
    """Obtains the next element of an iterator using the `__next__` magic method.

    This node is inserted in `for` loops and list comprehensions.
    """

    value: ast.expr

    _fields = ("value",)


class IterEnd(ast.expr):
    """Finalises an iterator using the `__end__` magic method.

    This node is inserted in `for` loops and list comprehensions. It is needed to
    consume linear iterators once they are finished.
    """

    value: ast.expr

    _fields = ("value",)


class DesugaredGenerator(ast.expr):
    """A single desugared generator in a list comprehension.

    Stores assignments of the original generator targets as well as dummy variables for
    the iterator and hasnext test.
    """

    iter_assign: ast.Assign
    hasnext_assign: ast.Assign
    next_assign: ast.Assign
    iterend: ast.expr
    iter: ast.Name
    hasnext: ast.Name
    ifs: list[ast.expr]

    _fields = (
        "iter_assign",
        "hasnext_assign",
        "next_assign",
        "iterend",
        "iter",
        "hasnext",
        "ifs",
    )


class DesugaredListComp(ast.expr):
    """A desugared list comprehension."""

    elt: ast.expr
    generators: list[DesugaredGenerator]

    _fields = (
        "elt",
        "generators",
    )


class PyExpr(ast.expr):
    """A compile-time evaluated `py(...)` expression."""

    value: ast.expr

    _fields = ("value",)


class NestedFunctionDef(ast.FunctionDef):
    cfg: "CFG"
    ty: FunctionType

    def __init__(self, cfg: "CFG", ty: FunctionType, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.cfg = cfg
        self.ty = ty


class CheckedNestedFunctionDef(ast.FunctionDef):
    cfg: "CheckedCFG"
    ty: FunctionType
    captured: Mapping[str, "Variable"]

    def __init__(
        self,
        cfg: "CheckedCFG",
        ty: FunctionType,
        captured: Mapping[str, "Variable"],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.cfg = cfg
        self.ty = ty
        self.captured = captured
