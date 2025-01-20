from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum, Flag, auto
from functools import cached_property, total_ordering
from typing import TYPE_CHECKING, ClassVar, TypeAlias, cast

import hugr.std.float
import hugr.std.int
from hugr import tys as ht

from guppylang.error import InternalGuppyError
from guppylang.tys.arg import Argument, ConstArg, TypeArg
from guppylang.tys.common import ToHugr, Transformable, Transformer, Visitor
from guppylang.tys.const import Const, ConstValue, ExistentialConstVar
from guppylang.tys.param import Parameter
from guppylang.tys.var import BoundVar, ExistentialVar

if TYPE_CHECKING:
    from guppylang.definition.struct import CheckedStructDef, StructField
    from guppylang.definition.ty import OpaqueTypeDef
    from guppylang.tys.subst import Inst, Subst


@dataclass(frozen=True)
class TypeBase(ToHugr[ht.Type], Transformable["Type"], ABC):
    """Abstract base class for all Guppy types.

    Note that all subclasses are expected to be immutable.
    """

    @cached_property
    @abstractmethod
    def copyable(self) -> bool:
        """Whether objects of this type can be implicitly copied."""

    @cached_property
    @abstractmethod
    def droppable(self) -> bool:
        """Whether objects of this type can be dropped."""

    @property
    def linear(self) -> bool:
        """Whether this type should be treated linearly."""
        return not self.copyable and not self.droppable

    @property
    def affine(self) -> bool:
        """Whether this type should be treated in an affine way."""
        return not self.copyable and self.droppable

    @cached_property
    @abstractmethod
    def hugr_bound(self) -> ht.TypeBound:
        """The Hugr bound of this type, i.e. `Any`, `Copyable`, or `Equatable`.

        This needs to be specified explicitly, since opaque nonlinear types in a Hugr
        extension could be either declared as copyable or equatable. If we don't get the
        bound exactly right during serialisation, the Hugr validator will complain.
        """

    @abstractmethod
    def cast(self) -> "Type":
        """Casts an implementor of `TypeBase` into a `Type`.

        This enforces that all implementors of `TypeBase` can be embedded into the
        `Type` union type.
        """

    @cached_property
    def unsolved_vars(self) -> set[ExistentialVar]:
        """The existential type variables contained in this type."""
        return set()

    def substitute(self, subst: "Subst") -> "Type":
        """Substitutes existential variables in this type."""
        from guppylang.tys.subst import Substituter

        return self.transform(Substituter(subst))

    def to_arg(self) -> TypeArg:
        """Wraps this constant into a type argument."""
        return TypeArg(self.cast())

    def __str__(self) -> str:
        """Returns a human-readable representation of the type."""
        from guppylang.tys.printing import TypePrinter

        # We use a custom printer that takes care of inserting parentheses and choosing
        # unique names
        return TypePrinter().visit(cast(Type, self))


@dataclass(frozen=True)
class ParametrizedTypeBase(TypeBase, ABC):
    """Abstract base class for types that depend on parameters.

    For example, `list`, `tuple`, etc. require arguments in order to be turned into a
    proper type.

    Note that all subclasses are expected to be immutable.
    """

    args: Sequence[Argument]

    def __post_init__(self) -> None:
        # Make sure that we don't have nested generic functions
        for arg in self.args:
            match arg:
                case TypeArg(ty=FunctionType(parametrized=True)):
                    raise InternalGuppyError(
                        "Tried to construct a higher-rank polymorphic type!"
                    )

    @property
    @abstractmethod
    def intrinsically_copyable(self) -> bool:
        """Whether this type is copyable, independent of the arguments.

        For example, a parametrized struct containing a qubit is never copyable, even if
        all its arguments are.
        """

    @cached_property
    def copyable(self) -> bool:
        """Whether this type should be treated as copyable."""
        # Either an argument isn't a type argument, or it must be copyable.
        return self.intrinsically_copyable and all(
            not isinstance(arg, TypeArg) or arg.ty.copyable for arg in self.args
        )

    @property
    @abstractmethod
    def intrinsically_droppable(self) -> bool:
        """Whether this type is droppable, independent of the arguments.

        For example, a parametrized struct containing a qubit is never droppable, even
        if all its arguments are.
        """

    @cached_property
    def droppable(self) -> bool:
        """Whether this type should be treated as copyable."""
        # Either an argument isn't a type argument, or it must be droppable.
        return self.intrinsically_droppable and all(
            not isinstance(arg, TypeArg) or arg.ty.droppable for arg in self.args
        )

    @cached_property
    def unsolved_vars(self) -> set[ExistentialVar]:
        """The existential type variables contained in this type."""
        return set().union(*(arg.unsolved_vars for arg in self.args))

    @cached_property
    def hugr_bound(self) -> ht.TypeBound:
        """The Hugr bound of this type, i.e. `Any`, `Copyable`, or `Equatable`."""
        if self.linear:
            return ht.TypeBound.Any
        return ht.TypeBound.join(
            *(arg.ty.hugr_bound for arg in self.args if isinstance(arg, TypeArg))
        )

    def visit(self, visitor: Visitor) -> None:
        """Accepts a visitor on this type."""
        if not visitor.visit(self):
            for arg in self.args:
                visitor.visit(arg)


@dataclass(frozen=True)
class BoundTypeVar(TypeBase, BoundVar):
    """Bound type variable, referencing a parameter of kind `Type`.

    For example, in the function type `forall T. list[T] -> T` we represent `T` as a
    `BoundTypeVar(idx=0)`.

    A bound type variables can be instantiated with a `TypeArg` argument.
    """

    copyable: bool
    droppable: bool

    @cached_property
    def hugr_bound(self) -> ht.TypeBound:
        """The Hugr bound of this type, i.e. `Any`, `Copyable`, or `Equatable`."""
        if self.linear:
            return ht.TypeBound.Any
        # We're conservative and don't require equatability for non-linear variables.
        # This is fine since Guppy doesn't use the equatable feature anyways.
        return ht.TypeBound.Copyable

    def cast(self) -> "Type":
        """Casts an implementor of `TypeBase` into a `Type`."""
        return self

    def to_hugr(self) -> ht.Variable:
        """Computes the Hugr representation of the type."""
        return ht.Variable(idx=self.idx, bound=self.hugr_bound)

    def visit(self, visitor: Visitor) -> None:
        """Accepts a visitor on this type."""
        visitor.visit(self)

    def transform(self, transformer: Transformer) -> "Type":
        """Accepts a transformer on this type."""
        return transformer.transform(self) or self

    def __str__(self) -> str:
        """Returns a human-readable representation of the type."""
        return self.display_name


@dataclass(frozen=True)
class ExistentialTypeVar(ExistentialVar, TypeBase):
    """Existential type variable.

    For example, the empty list literal `[]` is typed as `list[?T]` where `?T` stands
    for an existential type variable.

    During type checking we try to solve all existential type variables and substitute
    them with concrete types.
    """

    copyable: bool
    droppable: bool

    @classmethod
    def fresh(
        cls, display_name: str, copyable: bool, droppable: bool
    ) -> "ExistentialTypeVar":
        return ExistentialTypeVar(
            display_name, next(cls._fresh_id), copyable, droppable
        )

    @cached_property
    def unsolved_vars(self) -> set[ExistentialVar]:
        """The existential type variables contained in this type."""
        return {self}

    @cached_property
    def hugr_bound(self) -> ht.TypeBound:
        """The Hugr bound of this type, i.e. `Any`, `Copyable`, or `Equatable`."""
        raise InternalGuppyError(
            "Tried to compute bound of unsolved existential type variable"
        )

    def cast(self) -> "Type":
        """Casts an implementor of `TypeBase` into a `Type`."""
        return self

    def to_hugr(self) -> ht.Type:
        """Computes the Hugr representation of the type."""
        raise InternalGuppyError(
            "Tried to convert unsolved existential type variable to Hugr"
        )

    def visit(self, visitor: Visitor) -> None:
        """Accepts a visitor on this type."""
        visitor.visit(self)

    def transform(self, transformer: Transformer) -> "Type":
        """Accepts a transformer on this type."""
        return transformer.transform(self) or self


@dataclass(frozen=True)
class NoneType(TypeBase):
    """Type of `None`."""

    copyable: bool = field(default=True, init=True)
    droppable: bool = field(default=True, init=True)
    hugr_bound: ht.TypeBound = field(default=ht.TypeBound.Copyable, init=False)

    # Flag to avoid turning the type into a row when calling `type_to_row()`. This is
    # used to make sure that type vars instantiated to Nones are not broken up into
    # empty rows when generating a Hugr
    preserve: bool = field(default=False, compare=False)

    def cast(self) -> "Type":
        """Casts an implementor of `TypeBase` into a `Type`."""
        return self

    def to_hugr(self) -> ht.Tuple:
        """Computes the Hugr representation of the type."""
        return ht.Tuple()

    def visit(self, visitor: Visitor) -> None:
        """Accepts a visitor on this type."""
        visitor.visit(self)

    def transform(self, transformer: Transformer) -> "Type":
        """Accepts a transformer on this type."""
        return transformer.transform(self) or self


@dataclass(frozen=True)
class NumericType(TypeBase):
    """Numeric types like `int` and `float`."""

    kind: "Kind"

    @total_ordering
    class Kind(Enum):
        """The different kinds of numeric types."""

        Nat = auto()
        Int = auto()
        Float = auto()

        def __lt__(self, other: "NumericType.Kind") -> bool:
            return self.value < other.value

    INT_WIDTH: ClassVar[int] = 6

    @property
    def copyable(self) -> bool:
        """Whether objects of this type can be implicitly copied."""
        return True

    @property
    def droppable(self) -> bool:
        """Whether objects of this type can be dropped."""
        return True

    def cast(self) -> "Type":
        """Casts an implementor of `TypeBase` into a `Type`."""
        return self

    def to_hugr(self) -> ht.ExtType:
        """Computes the Hugr representation of the type."""
        match self.kind:
            case NumericType.Kind.Nat | NumericType.Kind.Int:
                return hugr.std.int.int_t(NumericType.INT_WIDTH)
            case NumericType.Kind.Float:
                return hugr.std.float.FLOAT_T

    @property
    def hugr_bound(self) -> ht.TypeBound:
        """The Hugr bound of this type, i.e. `Any` or `Copyable`"""
        return ht.TypeBound.Copyable

    def visit(self, visitor: Visitor) -> None:
        """Accepts a visitor on this type."""
        visitor.visit(self)

    def transform(self, transformer: Transformer) -> "Type":
        """Accepts a transformer on this type."""
        return transformer.transform(self) or self


class InputFlags(Flag):
    """Flags that can be set on inputs of function types.

    In the future, we could add  additional flags like `Frozen`.
    """

    NoFlags = 0
    Inout = auto()
    Owned = auto()


@dataclass(frozen=True)
class FuncInput:
    """A single input of a function type."""

    ty: "Type"
    flags: InputFlags


@dataclass(frozen=True, init=False)
class FunctionType(ParametrizedTypeBase):
    """Type of (potentially generic) functions."""

    inputs: Sequence[FuncInput]
    output: "Type"
    params: Sequence[Parameter]
    input_names: Sequence[str] | None

    args: Sequence[Argument] = field(init=False)
    copyable: bool = field(default=True, init=True)
    droppable: bool = field(default=True, init=True)
    intrinsically_copyable: bool = field(default=True, init=True)
    intrinsically_droppable: bool = field(default=True, init=True)
    hugr_bound: ht.TypeBound = field(default=ht.TypeBound.Copyable, init=False)

    def __init__(
        self,
        inputs: Sequence[FuncInput],
        output: "Type",
        input_names: Sequence[str] | None = None,
        params: Sequence[Parameter] | None = None,
    ) -> None:
        # We need a custom __init__ to set the args
        args = [TypeArg(inp.ty) for inp in inputs]
        args.append(TypeArg(output))
        object.__setattr__(self, "args", args)
        object.__setattr__(self, "inputs", inputs)
        object.__setattr__(self, "output", output)
        object.__setattr__(self, "input_names", input_names or [])
        object.__setattr__(self, "params", params or [])

    @property
    def parametrized(self) -> bool:
        """Whether the function is parametrized."""
        return len(self.params) > 0

    def cast(self) -> "Type":
        """Casts an implementor of `TypeBase` into a `Type`."""
        return self

    def to_hugr(self) -> ht.FunctionType:
        """Computes the Hugr representation of the type."""
        if self.parametrized:
            raise InternalGuppyError(
                "Tried to convert parametrised function type to Hugr. Use "
                "`to_hugr_poly` instead"
            )
        return self._to_hugr_function_type()

    def to_hugr_poly(self) -> ht.PolyFuncType:
        """Computes the Hugr `PolyFuncType` representation of the type."""
        func_ty = self._to_hugr_function_type()
        return ht.PolyFuncType(params=[p.to_hugr() for p in self.params], body=func_ty)

    def _to_hugr_function_type(self) -> ht.FunctionType:
        """Helper method to compute the Hugr `FunctionType` representation of the type.

        The resulting `FunctionType` can then be embedded into a Hugr `Type` or a Hugr
        `PolyFuncType`.
        """
        ins = [inp.ty.to_hugr() for inp in self.inputs]
        outs = [
            *(t.to_hugr() for t in type_to_row(self.output)),
            # We might have additional borrowed args that will be also outputted
            *(inp.ty.to_hugr() for inp in self.inputs if InputFlags.Inout in inp.flags),
        ]
        return ht.FunctionType(input=ins, output=outs)

    def visit(self, visitor: Visitor) -> None:
        """Accepts a visitor on this type."""
        if not visitor.visit(self):
            for inp in self.inputs:
                visitor.visit(inp)
            visitor.visit(self.output)
            for param in self.params:
                visitor.visit(param)

    def transform(self, transformer: Transformer) -> "Type":
        """Accepts a transformer on this type."""
        return transformer.transform(self) or FunctionType(
            [
                FuncInput(inp.ty.transform(transformer), inp.flags)
                for inp in self.inputs
            ],
            self.output.transform(transformer),
            self.input_names,
            self.params,
        )

    def instantiate(self, args: "Inst") -> "FunctionType":
        """Instantiates all function parameters with concrete types."""
        from guppylang.tys.subst import Instantiator

        assert len(args) == len(self.params)

        # Set the `preserve` flag for instantiated tuples and None
        preserved_args: list[Argument] = []
        for arg in args:
            if isinstance(arg, TypeArg):
                if isinstance(arg.ty, TupleType):
                    arg = TypeArg(TupleType(arg.ty.element_types, preserve=True))
                elif isinstance(arg.ty, NoneType):
                    arg = TypeArg(NoneType(preserve=True))
            preserved_args.append(arg)

        inst = Instantiator(preserved_args)
        return FunctionType(
            [FuncInput(inp.ty.transform(inst), inp.flags) for inp in self.inputs],
            self.output.transform(inst),
            self.input_names,
        )

    def unquantified(self) -> tuple["FunctionType", Sequence[ExistentialVar]]:
        """Instantiates all parameters with existential variables."""
        exs = [param.to_existential() for param in self.params]
        return self.instantiate([arg for arg, _ in exs]), [var for _, var in exs]


@dataclass(frozen=True, init=False)
class TupleType(ParametrizedTypeBase):
    """Type of tuples."""

    element_types: Sequence["Type"]

    # Flag to avoid turning the tuple into a row when calling `type_to_row()`. This is
    # used to make sure that type vars instantiated to tuples are not broken up into
    # rows when generating a Hugr
    preserve: bool = field(default=False, compare=False)

    def __init__(self, element_types: Sequence["Type"], preserve: bool = False) -> None:
        # We need a custom __init__ to set the args
        args = [TypeArg(ty) for ty in element_types]
        object.__setattr__(self, "args", args)
        object.__setattr__(self, "element_types", element_types)
        object.__setattr__(self, "preserve", preserve)

    @property
    def intrinsically_copyable(self) -> bool:
        """Whether objects of this type can be implicitly copied."""
        return True

    @property
    def intrinsically_droppable(self) -> bool:
        """Whether objects of this type can be dropped."""
        return True

    def cast(self) -> "Type":
        """Casts an implementor of `TypeBase` into a `Type`."""
        return self

    def to_hugr(self) -> ht.Tuple:
        """Computes the Hugr representation of the type."""
        return ht.Tuple(*row_to_hugr(self.element_types))

    def transform(self, transformer: Transformer) -> "Type":
        """Accepts a transformer on this type."""
        return transformer.transform(self) or TupleType(
            [ty.transform(transformer) for ty in self.element_types], self.preserve
        )


@dataclass(frozen=True, init=False)
class SumType(ParametrizedTypeBase):
    """Type of sums.

    Note that this type is only used internally when constructing the Hugr. Users cannot
    write down this type.
    """

    element_types: Sequence["Type"]

    def __init__(self, element_types: Sequence["Type"]) -> None:
        # We need a custom __init__ to set the args
        args = [TypeArg(ty) for ty in element_types]
        object.__setattr__(self, "args", args)
        object.__setattr__(self, "element_types", element_types)

    @property
    def intrinsically_copyable(self) -> bool:
        """Whether objects of this type can be implicitly copied."""
        return True

    @property
    def intrinsically_droppable(self) -> bool:
        """Whether objects of this type can be dropped."""
        return True

    def cast(self) -> "Type":
        """Casts an implementor of `TypeBase` into a `Type`."""
        return self

    def to_hugr(self) -> ht.Sum:
        """Computes the Hugr representation of the type."""
        rows = [type_to_row(ty) for ty in self.element_types]
        if all(len(row) == 0 for row in rows):
            return ht.UnitSum(size=len(rows))
        elif len(rows) == 1:
            return ht.Tuple(*row_to_hugr(rows[0]))
        else:
            return ht.Sum(variant_rows=rows_to_hugr(rows))

    def transform(self, transformer: Transformer) -> "Type":
        """Accepts a transformer on this type."""
        return transformer.transform(self) or SumType(
            [ty.transform(transformer) for ty in self.element_types]
        )


@dataclass(frozen=True)
class OpaqueType(ParametrizedTypeBase):
    """Type that is directly backed by a Hugr opaque type.

    For example, many builtin types like `int`, `float`, `list` etc. are directly backed
    by a Hugr extension.
    """

    defn: "OpaqueTypeDef"

    @property
    def intrinsically_copyable(self) -> bool:
        """Whether objects of this type can be implicitly copied."""
        return not self.defn.never_copyable

    @property
    def intrinsically_droppable(self) -> bool:
        """Whether objects of this type can be dropped."""
        return not self.defn.never_droppable

    @property
    def hugr_bound(self) -> ht.TypeBound:
        """The Hugr bound of this type, i.e. `Any`, `Copyable`, or `Equatable`."""
        if self.defn.bound is not None:
            return self.defn.bound
        return super().hugr_bound

    def cast(self) -> "Type":
        """Casts an implementor of `TypeBase` into a `Type`."""
        return self

    def to_hugr(self) -> ht.Type:
        """Computes the Hugr representation of the type."""
        return self.defn.to_hugr(self.args)

    def transform(self, transformer: Transformer) -> "Type":
        """Accepts a transformer on this type."""
        return transformer.transform(self) or OpaqueType(
            [arg.transform(transformer) for arg in self.args], self.defn
        )


@dataclass(frozen=True)
class StructType(ParametrizedTypeBase):
    """A struct type."""

    defn: "CheckedStructDef"

    @cached_property
    def fields(self) -> list["StructField"]:
        """The fields of this struct type."""
        from guppylang.definition.struct import StructField
        from guppylang.tys.subst import Instantiator

        inst = Instantiator(self.args)
        return [StructField(f.name, f.ty.transform(inst)) for f in self.defn.fields]

    @cached_property
    def field_dict(self) -> "dict[str, StructField]":
        """Mapping from names to fields of this struct type."""
        return {field.name: field for field in self.fields}

    @cached_property
    def intrinsically_copyable(self) -> bool:
        """Whether objects of this type can be  implicitly copied."""
        return all(f.ty.copyable for f in self.fields)

    @cached_property
    def intrinsically_droppable(self) -> bool:
        """Whether objects of this type can be dropped."""
        return all(f.ty.droppable for f in self.fields)

    def cast(self) -> "Type":
        """Casts an implementor of `TypeBase` into a `Type`."""
        return self

    def to_hugr(self) -> ht.Tuple:
        """Computes the Hugr representation of the type."""
        return ht.Tuple(*(f.ty.to_hugr() for f in self.fields))

    def transform(self, transformer: Transformer) -> "Type":
        """Accepts a transformer on this type."""
        return transformer.transform(self) or StructType(
            [arg.transform(transformer) for arg in self.args], self.defn
        )


#: The type of parametrized Guppy types.
ParametrizedType: TypeAlias = (
    FunctionType | TupleType | SumType | OpaqueType | StructType
)

#: The type of Guppy types.
#:
#: This is a type alias for a union of all Guppy types defined in this module. This
#: models an algebraic data type and enables exhaustiveness checking in pattern matches
#: etc.
#:
#: This might become obsolete in case the @sealed decorator is added:
#:   * https://peps.python.org/pep-0622/#sealed-classes-as-algebraic-data-types
#:   * https://github.com/johnthagen/sealed-typing-pep
Type: TypeAlias = (
    BoundTypeVar | ExistentialTypeVar | NumericType | NoneType | ParametrizedType
)

#: An immutable row of Guppy types.
TypeRow: TypeAlias = Sequence[Type]


def row_to_type(row: TypeRow) -> Type:
    """Turns a row of types into a single type by packing into a tuple."""
    if len(row) == 0:
        return NoneType()
    elif len(row) == 1:
        return row[0]
    else:
        return TupleType(row)


def type_to_row(ty: Type) -> TypeRow:
    """Turns a type into a row of types by unpacking top-level tuples."""
    if isinstance(ty, NoneType) and not ty.preserve:
        return []
    if isinstance(ty, TupleType) and not ty.preserve:
        return ty.element_types
    return [ty]


def row_to_hugr(row: TypeRow) -> ht.TypeRow:
    """Computes the Hugr representation of a type row."""
    return [ty.to_hugr() for ty in row]


def rows_to_hugr(rows: Sequence[TypeRow]) -> list[ht.TypeRow]:
    """Computes the Hugr representation of a sequence of rows."""
    return [row_to_hugr(row) for row in rows]


def unify(s: Type | Const, t: Type | Const, subst: "Subst | None") -> "Subst | None":
    """Computes a most general unifier for two types or constants.

    Return a substitutions `subst` such that `s[subst] == t[subst]` or `None` if this
    not possible.
    """
    # Make sure that s and t are either both constants or both types
    assert isinstance(s, TypeBase) == isinstance(t, TypeBase)
    if subst is None:
        return None
    match s, t:
        case ExistentialVar(id=s_id), ExistentialVar(id=t_id) if s_id == t_id:
            return subst
        case ExistentialTypeVar() | ExistentialConstVar() as s_var, t:
            return _unify_var(s_var, t, subst)
        case s, ExistentialTypeVar() | ExistentialConstVar() as t_var:
            return _unify_var(t_var, s, subst)
        case BoundVar(idx=s_idx), BoundVar(idx=t_idx) if s_idx == t_idx:
            return subst
        case ConstValue(value=c_value), ConstValue(value=d_value) if c_value == d_value:
            return subst
        case NumericType(kind=s_kind), NumericType(kind=t_kind) if s_kind == t_kind:
            return subst
        case NoneType(), NoneType():
            return subst
        case FunctionType() as s, FunctionType() as t if s.params == t.params:
            if len(s.inputs) != len(t.inputs):
                return None
            for a, b in zip(s.inputs, t.inputs, strict=True):
                if a.ty.linear and b.ty.linear and a.flags != b.flags:
                    return None
            return _unify_args(s, t, subst)
        case TupleType() as s, TupleType() as t:
            return _unify_args(s, t, subst)
        case SumType() as s, SumType() as t:
            return _unify_args(s, t, subst)
        case OpaqueType() as s, OpaqueType() as t if s.defn == t.defn:
            return _unify_args(s, t, subst)
        case StructType() as s, StructType() as t if s.defn == t.defn:
            return _unify_args(s, t, subst)
        case _:
            return None


def _unify_var(
    var: ExistentialTypeVar | ExistentialConstVar, t: Type | Const, subst: "Subst"
) -> "Subst | None":
    """Helper function for unification of type or const variables."""
    if var in subst:
        return unify(subst[var], t, subst)
    if isinstance(t, ExistentialTypeVar) and t in subst:
        return unify(var, subst[t], subst)
    if var in t.unsolved_vars:
        return None
    return {var: t, **subst}


def _unify_args(
    s: ParametrizedType, t: ParametrizedType, subst: "Subst"
) -> "Subst | None":
    """Helper function for unification of type arguments of parametrised types."""
    if len(s.args) != len(t.args):
        return None
    for sa, ta in zip(s.args, t.args, strict=True):
        match sa, ta:
            case TypeArg(ty=sa_ty), TypeArg(ty=ta_ty):
                res = unify(sa_ty, ta_ty, subst)
                if res is None:
                    return None
                subst = res
            case ConstArg(const=sa_const), ConstArg(const=ta_const):
                res = unify(sa_const, ta_const, subst)
                if res is None:
                    return None
                subst = res
            case _:
                return None
    return subst


### Helpers for working with tuples of functions


def parse_function_tensor(ty: TupleType) -> list[FunctionType] | None:
    """Parses a nested tuple of function types into a flat list of functions."""
    result = []
    for el in ty.element_types:
        if isinstance(el, FunctionType):
            result.append(el)
        elif isinstance(el, TupleType):
            funcs = parse_function_tensor(el)
            if funcs:
                result.extend(funcs)
            else:
                return None
    return result


def function_tensor_signature(tys: list[FunctionType]) -> FunctionType:
    """Compute the combined function signature of a list of functions"""
    inputs: list[FuncInput] = []
    outputs: list[Type] = []
    for fun_ty in tys:
        assert not fun_ty.parametrized
        inputs.extend(fun_ty.inputs)
        outputs.extend(type_to_row(fun_ty.output))
    return FunctionType(inputs, row_to_type(outputs))
