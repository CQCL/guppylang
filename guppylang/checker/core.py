import ast
import copy
import itertools
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field, replace
from functools import cached_property
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    NamedTuple,
    TypeAlias,
    TypeVar,
)

from typing_extensions import assert_never

from guppylang.ast_util import AstNode, name_nodes_in_ast
from guppylang.cfg.bb import VId
from guppylang.definition.common import DefId, Definition
from guppylang.definition.ty import TypeDef
from guppylang.definition.value import CallableDef
from guppylang.tys.builtin import (
    array_type_def,
    bool_type_def,
    callable_type_def,
    float_type_def,
    frozenarray_type_def,
    int_type_def,
    list_type_def,
    nat_type_def,
    none_type_def,
    option_type_def,
    sized_iter_type_def,
    string_type_def,
    tuple_type_def,
)
from guppylang.tys.param import Parameter
from guppylang.tys.ty import (
    BoundTypeVar,
    ExistentialTypeVar,
    FunctionType,
    InputFlags,
    NoneType,
    NumericType,
    OpaqueType,
    StructType,
    SumType,
    TupleType,
    Type,
)

if TYPE_CHECKING:
    from guppylang.definition.struct import StructField


#: A "place" is a description for a storage location of a local value that users
#: can refer to in their program.
#:
#: Roughly, these are values that can be lowered to a static wire within the Hugr
#: representation. The most basic example of a place is a single local variable. Beyond
#: that, we also treat some projections of local variables (e.g. nested struct field
#: accesses) as places.
#:
#: All places are equipped with a unique id, a type and an optional definition AST
#: location. During linearity checking, they are tracked separately.
Place: TypeAlias = "Variable | FieldAccess | SubscriptAccess"

#: Unique identifier for a `Place`.
PlaceId: TypeAlias = "Variable.Id | FieldAccess.Id | SubscriptAccess.Id"


@dataclass(frozen=True)
class Variable:
    """A place identifying a local variable."""

    name: str
    ty: Type
    defined_at: AstNode | None
    flags: InputFlags = InputFlags.NoFlags

    @dataclass(frozen=True)
    class Id:
        """Identifier for variable places."""

        name: str

    @cached_property
    def id(self) -> "Variable.Id":
        """The unique `PlaceId` identifier for this place."""
        return Variable.Id(self.name)

    @cached_property
    def root(self) -> "Variable":
        """The root variable of this place."""
        return self

    @property
    def describe(self) -> str:
        """A human-readable description of this place for error messages."""
        return f"Variable `{self}`"

    def __str__(self) -> str:
        """String representation of this place."""
        return self.name

    def replace_defined_at(self, node: AstNode | None) -> "Variable":
        """Returns a new `Variable` instance with an updated definition location."""
        return replace(self, defined_at=node)


@dataclass(frozen=True)
class FieldAccess:
    """A place identifying a field access on a local struct."""

    parent: Place
    field: "StructField"
    exact_defined_at: AstNode | None

    @dataclass(frozen=True)
    class Id:
        """Identifier for field places."""

        parent: PlaceId
        field: str

    def __post_init__(self) -> None:
        # Check that the field access is consistent
        assert self.struct_ty.field_dict[self.field.name] == self.field

    @cached_property
    def id(self) -> "FieldAccess.Id":
        """The unique `PlaceId` identifier for this place."""
        return FieldAccess.Id(self.parent.id, self.field.name)

    @cached_property
    def root(self) -> "Variable":
        """The root variable of this place."""
        return self.parent.root

    @property
    def ty(self) -> Type:
        """The type of this place."""
        return self.field.ty

    @cached_property
    def struct_ty(self) -> StructType:
        """The type of the struct whose field is accessed."""
        assert isinstance(self.parent.ty, StructType)
        return self.parent.ty

    @cached_property
    def defined_at(self) -> AstNode | None:
        """Optional location where this place was last assigned to."""
        return self.exact_defined_at or self.parent.defined_at

    @cached_property
    def describe(self) -> str:
        """A human-readable description of this place for error messages."""
        return f"Field `{self}`"

    def __str__(self) -> str:
        """String representation of this place."""
        return f"{self.parent}.{self.field.name}"

    def replace_defined_at(self, node: AstNode | None) -> "FieldAccess":
        """Returns a new `FieldAccess` instance with an updated definition location."""
        return replace(self, exact_defined_at=node)


class SetitemCall(NamedTuple):
    """
    Represents a `__setitem__` call for assigning values to array elements.

    Holds the expression corresponding to the `__setitem__` call and the variable
    holding the value to be written to the subscript.
    """

    #: Expression corresponding to the `__setitem__` call.
    call: ast.expr

    #: Variable holding the value that should be written to the subscript.
    #: This variable *must be* assigned before compiling the call!
    value_var: Variable


@dataclass(frozen=True)
class SubscriptAccess:
    """A place identifying a subscript `place[item]` access."""

    parent: Place
    item: Variable
    ty: Type
    item_expr: ast.expr
    getitem_call: ast.expr | None = None
    setitem_call: SetitemCall | None = None

    @dataclass(frozen=True)
    class Id:
        """Identifier for subscript places."""

        parent: PlaceId
        item: Variable.Id

    @cached_property
    def id(self) -> "SubscriptAccess.Id":
        """The unique `PlaceId` identifier for this place."""
        return SubscriptAccess.Id(self.parent.id, self.item.id)

    @cached_property
    def defined_at(self) -> AstNode | None:
        """Optional location where this place was last assigned to."""
        return self.parent.defined_at

    @cached_property
    def root(self) -> "Variable":
        """The root variable of this place."""
        return self.parent.root

    @property
    def describe(self) -> str:
        """A human-readable description of this place for error messages."""
        return f"Subscript `{self}`"

    def __str__(self) -> str:
        """String representation of this place."""
        return f"{self.parent}[...]"


def contains_subscript(place: Place) -> SubscriptAccess | None:
    """Checks if a place contains a subscript access and returns the rightmost one."""
    while not isinstance(place, Variable):
        if isinstance(place, SubscriptAccess):
            return place
        place = place.parent
    return None


PyScope = dict[str, Any]


@dataclass(frozen=True)
class Globals:
    """Collection of definitions that are available on module-level.

    Stores a mapping from global ids to their definition together with a mapping of
    user names to definition id and instance implementation id.
    """

    defs: dict[DefId, Definition]

    names: dict[str, DefId]
    impls: dict[DefId, dict[str, DefId]]
    python_scope: PyScope = field(repr=False)

    @staticmethod
    def default() -> "Globals":
        """Generates a `Globals` instance that is populated with all core types"""
        builtins: list[Definition] = [
            callable_type_def,
            tuple_type_def,
            none_type_def,
            bool_type_def,
            nat_type_def,
            int_type_def,
            float_type_def,
            string_type_def,
            list_type_def,
            array_type_def,
            frozenarray_type_def,
            sized_iter_type_def,
            option_type_def,
        ]
        defs = {defn.id: defn for defn in builtins}
        names = {defn.name: defn.id for defn in builtins}
        return Globals(defs, names, {}, {})

    def get_instance_func(self, ty: Type | TypeDef, name: str) -> CallableDef | None:
        """Looks up an instance function with a given name for a type.

        Returns `None` if the name doesn't exist or isn't a function.
        """
        type_defn: TypeDef
        match ty:
            case TypeDef() as type_defn:
                pass
            case BoundTypeVar() | ExistentialTypeVar() | SumType():
                return None
            case NumericType(kind):
                match kind:
                    case NumericType.Kind.Nat:
                        type_defn = nat_type_def
                    case NumericType.Kind.Int:
                        type_defn = int_type_def
                    case NumericType.Kind.Float:
                        type_defn = float_type_def
                    case kind:
                        return assert_never(kind)
            case FunctionType():
                type_defn = callable_type_def
            case OpaqueType() as ty:
                type_defn = ty.defn
            case StructType() as ty:
                type_defn = ty.defn
            case TupleType():
                type_defn = tuple_type_def
            case NoneType():
                type_defn = none_type_def
            case _:
                return assert_never(ty)

        if type_defn.id in self.impls and name in self.impls[type_defn.id]:
            def_id = self.impls[type_defn.id][name]
            defn = self.defs[def_id]
            if isinstance(defn, CallableDef):
                return defn
        return None

    def with_python_scope(self, python_scope: PyScope) -> "Globals":
        return Globals(
            self.defs, self.names, self.impls, self.python_scope | python_scope
        )

    def __or__(self, other: "Globals") -> "Globals":
        impls = {
            def_id: self.impls.get(def_id, {}) | other.impls.get(def_id, {})
            for def_id in self.impls.keys() | other.impls.keys()
        }
        return Globals(
            {**self.defs, **other.defs},  # Can't use `|` since it's a Mapping
            self.names | other.names,
            impls,
            self.python_scope | other.python_scope,
        )

    def __contains__(self, item: DefId | str) -> bool:
        match item:
            case DefId() as def_id:
                return def_id in self.defs
            case str(name):
                return name in self.names
            case x:
                return assert_never(x)

    def __getitem__(self, item: DefId | str) -> Definition:
        match item:
            case DefId() as def_id:
                return self.defs[def_id]
            case str(name):
                return self.defs[self.names[name]]
            case x:
                return assert_never(x)


V = TypeVar("V")


@dataclass
class Locals(Generic[VId, V]):
    """Scoped mapping from program variable ids to the corresponding program variable.

    Depending on which checking phase we are in (type checking or linearity checking),
    we use this either as a mapping from strings to `Variable`s or as a mapping from
    `PlaceId`s to `Place`s.
    """

    vars: dict[VId, V]
    parent_scope: "Locals[VId, V] | None" = None

    def __getitem__(self, item: VId) -> V:
        if item not in self.vars and self.parent_scope:
            return self.parent_scope[item]

        return self.vars[item]

    def __setitem__(self, key: VId, value: V) -> None:
        self.vars[key] = value

    def __iter__(self) -> Iterator[VId]:
        parent_iter = iter(self.parent_scope) if self.parent_scope else iter(())
        return itertools.chain(iter(self.vars), parent_iter)

    def __contains__(self, item: VId) -> bool:
        return (item in self.vars) or (
            self.parent_scope is not None and item in self.parent_scope
        )

    def __copy__(self) -> "Locals[VId, V]":
        # Make a copy of the var map so that mutating the copy doesn't
        # mutate our variable mapping
        return Locals(self.vars.copy(), copy.copy(self.parent_scope))

    def keys(self) -> set[VId]:
        parent_keys = self.parent_scope.keys() if self.parent_scope else set()
        return parent_keys | self.vars.keys()

    def values(self) -> Iterable[V]:
        parent_values = (
            iter(self.parent_scope.values()) if self.parent_scope else iter(())
        )
        return itertools.chain(self.vars.values(), parent_values)

    def items(self) -> Iterable[tuple[VId, V]]:
        parent_items = (
            iter(self.parent_scope.items()) if self.parent_scope else iter(())
        )
        return itertools.chain(self.vars.items(), parent_items)


class Context(NamedTuple):
    """The type checking context."""

    globals: Globals
    locals: Locals[str, Variable]
    generic_params: dict[str, Parameter]


class DummyEvalDict(PyScope):
    """A custom dict that can be passed to `eval` to give better error messages.
    This class is used to implement the `py(...)` expression. If the user tries to
    access a Guppy variable in the Python context, we give an informative error message.
    """

    ctx: Context
    node: ast.expr

    @dataclass
    class GuppyVarUsedError(BaseException):
        """Error that is raised when the user tries to access a Guppy variable."""

        var: str
        node: ast.Name | None

    def __init__(self, ctx: Context, node: ast.expr):
        super().__init__(**ctx.globals.python_scope)
        self.ctx = ctx
        self.node = node

    def _check_item(self, key: str) -> None:
        # Catch the user trying to access Guppy variables
        if key in self.ctx.locals:
            # Find the name node in the AST where the usage occurs
            n = next((n for n in name_nodes_in_ast(self.node) if n.id == key), None)
            raise self.GuppyVarUsedError(key, n)

    def __getitem__(self, key: str) -> Any:
        self._check_item(key)
        return super().__getitem__(key)

    def __delitem__(self, key: str) -> None:
        self._check_item(key)
        super().__delitem__(key)

    def __contains__(self, key: object) -> bool:
        if isinstance(key, str) and key in self.ctx.locals:
            return True
        return super().__contains__(key)
