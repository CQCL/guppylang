"""Custom AST nodes used by Guppy"""

import ast
from collections.abc import Mapping
from enum import Enum
from typing import TYPE_CHECKING, Any

from guppylang.ast_util import AstNode
from guppylang.tys.const import Const
from guppylang.tys.subst import Inst
from guppylang.tys.ty import FunctionType, StructType, Type

if TYPE_CHECKING:
    from guppylang.cfg.cfg import CFG
    from guppylang.checker.cfg_checker import CheckedCFG
    from guppylang.checker.core import Place, Variable
    from guppylang.definition.common import DefId
    from guppylang.definition.struct import StructField
    from guppylang.tys.param import ConstParam


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


class GenericParamValue(ast.Name):
    id: str
    param: "ConstParam"

    _fields = (
        "id",
        "param",
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
    tensor_ty: FunctionType

    _fields = (
        "func",
        "args",
        "tensor_ty",
    )


class TypeApply(ast.expr):
    value: ast.expr
    inst: Inst

    _fields = (
        "value",
        "inst",
    )


class PartialApply(ast.expr):
    """A partial function application.

    This node is emitted when methods are loaded as values, since this requires
    partially applying the `self` argument.
    """

    func: ast.expr
    args: list[ast.expr]

    _fields = (
        "func",
        "args",
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


class SubscriptAccessAndDrop(ast.expr):
    """A subscript element access on an object, dropping all the remaining items."""

    item: "Variable"
    item_expr: ast.expr
    getitem_expr: ast.expr
    original_expr: ast.Subscript

    _fields = ("item", "item_expr", "getitem_expr", "original_expr")


class MakeIter(ast.expr):
    """Creates an iterator using the `__iter__` magic method.

    This node is inserted in `for` loops and list comprehensions.
    """

    value: ast.expr
    unwrap_size_hint: bool

    # Node that triggered the creation of this iterator. For example, a for loop stmt.
    # It is not mentioned in `_fields` so that it is not visible to AST visitors
    origin_node: ast.AST

    _fields = ("value",)

    def __init__(
        self, value: ast.expr, origin_node: ast.AST, unwrap_size_hint: bool = True
    ) -> None:
        super().__init__(value)
        self.origin_node = origin_node
        self.unwrap_size_hint = unwrap_size_hint


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
    next_call: ast.expr
    iter: ast.expr
    target: ast.expr
    ifs: list[ast.expr]

    borrowed_outer_places: "list[Place]"

    _fields = (
        "iter_assign",
        "next_call",
        "iter",
        "target",
        "ifs",
    )


class DesugaredGeneratorExpr(ast.expr):
    """A desugared generator expression."""

    elt: ast.expr
    generators: list[DesugaredGenerator]

    _fields = (
        "elt",
        "generators",
    )


class DesugaredListComp(ast.expr):
    """A desugared list comprehension."""

    elt: ast.expr
    generators: list[DesugaredGenerator]

    _fields = (
        "elt",
        "generators",
    )


class DesugaredArrayComp(ast.expr):
    """A desugared array comprehension."""

    elt: ast.expr
    generator: DesugaredGenerator
    length: Const
    elt_ty: Type

    _fields = (
        "elt",
        "generator",
        "length",
        "elt_ty",
    )


class ComptimeExpr(ast.expr):
    """A compile-time evaluated `py(...)` expression."""

    value: ast.expr

    _fields = ("value",)


class ResultExpr(ast.expr):
    """A `result(tag, value)` expression."""

    value: ast.expr
    base_ty: Type
    #: Array length in case this is an array result, otherwise `None`
    array_len: Const | None
    tag: str

    _fields = ("value", "base_ty", "array_len", "tag")

    @property
    def args(self) -> list[ast.expr]:
        return [self.value]


class ExitKind(Enum):
    ExitShot = 0  # Exit the current shot
    Panic = 1  # Panic the program ending all shots


class PanicExpr(ast.expr):
    """A `panic(msg, *args)` or `exit(msg, *args)` expression ."""

    kind: ExitKind
    signal: int
    msg: str
    values: list[ast.expr]

    _fields = ("kind", "signal", "msg", "values")


class BarrierExpr(ast.expr):
    """A `barrier(*args)` expression."""

    args: list[ast.expr]
    func_ty: FunctionType
    _fields = ("args", "func_ty")


AnyCall = LocalCall | GlobalCall | TensorCall | BarrierExpr | ResultExpr


class InoutReturnSentinel(ast.expr):
    """An invisible expression corresponding to an implicit use of borrowed vars
    whenever a function returns."""

    var: "Place | str"

    _fields = ("var",)


class UnpackPattern(ast.expr):
    """The LHS of an unpacking assignment like `a, *bs, c = ...` or
    `[a, *bs, c] = ...`."""

    #: Patterns occurring on the left of the starred target
    left: list[ast.expr]

    #: The starred target or `None` if there is none
    starred: ast.expr | None

    #: Patterns occurring on the right of the starred target. This will be an empty list
    #: if there is no starred target
    right: list[ast.expr]

    _fields = ("left", "starred", "right")


class TupleUnpack(ast.expr):
    """The LHS of an unpacking assignment of a tuple."""

    #: The (possibly starred) unpacking pattern
    pattern: UnpackPattern

    _fields = ("pattern",)


class IterableUnpack(ast.expr):
    """The LHS of an unpacking assignment of an iterable type."""

    #: The (possibly starred) unpacking pattern
    pattern: UnpackPattern

    #: Comprehension that collects the RHS iterable into an array
    compr: DesugaredArrayComp

    #: Dummy variable that the RHS should be bound to. This variable is referenced in
    #: `compr`
    rhs_var: PlaceNode

    # Don't mention the comprehension in _fields to avoid visitors recursing it
    _fields = ("pattern",)

    def __init__(
        self, pattern: UnpackPattern, compr: DesugaredArrayComp, rhs_var: PlaceNode
    ) -> None:
        super().__init__(pattern)
        self.compr = compr
        self.rhs_var = rhs_var


#: Any unpacking operation.
AnyUnpack = TupleUnpack | IterableUnpack


class NestedFunctionDef(ast.FunctionDef):
    cfg: "CFG"
    ty: FunctionType
    docstring: str | None

    def __init__(self, cfg: "CFG", ty: FunctionType, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.cfg = cfg
        self.ty = ty


class CheckedNestedFunctionDef(ast.FunctionDef):
    def_id: "DefId"
    cfg: "CheckedCFG[Place]"
    ty: FunctionType

    #: Mapping from names to variables captured by this function, together with an AST
    #: node witnessing a use of the captured variable in the function body.
    captured: Mapping[str, tuple["Variable", AstNode]]

    def __init__(
        self,
        def_id: "DefId",
        cfg: "CheckedCFG[Place]",
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
