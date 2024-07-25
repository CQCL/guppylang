"""Custom AST nodes used by Guppy"""

import ast
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from guppylang.ast_util import AstNode
from guppylang.tys.subst import Inst
from guppylang.tys.ty import FunctionType, StructType, Type

if TYPE_CHECKING:
    from guppylang.cfg.cfg import CFG
    from guppylang.checker.cfg_checker import CheckedCFG
    from guppylang.checker.core import Place, Variable
    from guppylang.definition.common import DefId
    from guppylang.definition.struct import StructField


class PlaceNode(ast.expr):
    place: "Place"

    _fields = ("place",)


class GlobalName(ast.Name):
    id: str
    def_id: "DefId"

    _fields = (
        "id",
        "def_id",
    )


class LocalCall(ast.expr):
    func: ast.expr
    args: list[ast.expr]

    _fields = (
        "func",
        "args",
    )


class GlobalCall(ast.expr):
    def_id: "DefId"
    args: list[ast.expr]
    type_args: Inst  # Inferred type arguments

    _fields = (
        "def_id",
        "args",
        "type_args",
    )


class TensorCall(ast.expr):
    """A call to a tuple of functions. Behaves like a local call, but more
    unpacking of tuples is required at compilation"""

    func: ast.expr
    args: list[ast.expr]
    out_tys: Type

    _fields = (
        "func",
        "args",
        "out_tys",
    )


class TypeApply(ast.expr):
    value: ast.expr
    inst: Inst

    _fields = (
        "value",
        "inst",
    )


class FieldAccessAndDrop(ast.expr):
    """A field access on a struct, dropping all the remaining other fields."""

    value: ast.expr
    struct_ty: "StructType"
    field: "StructField"

    _fields = (
        "value",
        "struct_ty",
        "field",
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
    iter: ast.expr
    hasnext: ast.expr
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


class ResultExpr(ast.expr):
    """A `result(tag, value)` expression."""

    value: ast.expr
    ty: Type
    tag: int

    _fields = ("value", "ty", "tag")


class NestedFunctionDef(ast.FunctionDef):
    cfg: "CFG"
    ty: FunctionType

    def __init__(self, cfg: "CFG", ty: FunctionType, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.cfg = cfg
        self.ty = ty


class CheckedNestedFunctionDef(ast.FunctionDef):
    def_id: "DefId"
    cfg: "CheckedCFG"
    ty: FunctionType

    #: Mapping from names to variables captured by this function, together with an AST
    #: node witnessing a use of the captured variable in the function body.
    captured: Mapping[str, tuple["Variable", AstNode]]

    def __init__(
        self,
        def_id: "DefId",
        cfg: "CheckedCFG",
        ty: FunctionType,
        captured: Mapping[str, tuple["Variable", AstNode]],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.def_id = def_id
        self.cfg = cfg
        self.ty = ty
        self.captured = captured
