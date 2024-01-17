import ast
import itertools
from abc import ABC, abstractmethod
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    ClassVar,
    Literal,
)

import guppylang.hugr.tys as tys
from guppylang.ast_util import AstNode

if TYPE_CHECKING:
    from guppylang.checker.core import Globals


Subst = dict["ExistentialTypeVar", "GuppyType"]
Inst = Sequence["GuppyType"]


@dataclass(frozen=True)
class GuppyType(ABC):
    """Base class for all Guppy types.

    Note that all instances of `GuppyType` subclasses are expected to be immutable.
    """

    name: ClassVar[str]

    # Cache for free variables
    _unsolved_vars: set["ExistentialTypeVar"] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        # Make sure that we don't have higher-rank polymorphic types
        for arg in self.type_args:
            if isinstance(arg, FunctionType) and arg.quantified:
                from guppylang.error import InternalGuppyError

                raise InternalGuppyError(
                    "Tried to construct a higher-rank polymorphic type!"
                )

        # Compute free variables
        if isinstance(self, ExistentialTypeVar):
            vs = {self}
        else:
            vs = set()
            for arg in self.type_args:
                vs |= arg.unsolved_vars
        object.__setattr__(self, "_unsolved_vars", vs)

    @staticmethod
    @abstractmethod
    def build(*args: "GuppyType", node: AstNode | None = None) -> "GuppyType":
        pass

    @property
    @abstractmethod
    def type_args(self) -> Iterator["GuppyType"]:
        pass

    @property
    @abstractmethod
    def linear(self) -> bool:
        pass

    @abstractmethod
    def to_hugr(self) -> tys.Type:
        pass

    @abstractmethod
    def transform(self, transformer: "TypeTransformer") -> "GuppyType":
        pass

    def hugr_bound(self) -> tys.TypeBound:
        if self.linear:
            return tys.TypeBound.Any
        return tys.TypeBound.join(*(ty.hugr_bound() for ty in self.type_args))

    @property
    def unsolved_vars(self) -> set["ExistentialTypeVar"]:
        return self._unsolved_vars

    def substitute(self, s: Subst) -> "GuppyType":
        return self.transform(Substituter(s))


@dataclass(frozen=True)
class BoundTypeVar(GuppyType):
    """Bound type variable, identified with a de Bruijn index."""

    idx: int
    display_name: str
    linear: bool = False

    name: ClassVar[Literal["BoundTypeVar"]] = "BoundTypeVar"

    @staticmethod
    def build(*rgs: GuppyType, node: AstNode | None = None) -> GuppyType:
        raise NotImplementedError

    @property
    def type_args(self) -> Iterator["GuppyType"]:
        return iter(())

    def hugr_bound(self) -> tys.TypeBound:
        # We shouldn't make variables equatable, since we also want to substitute types
        # like `float`
        return tys.TypeBound.Any if self.linear else tys.TypeBound.Copyable

    def transform(self, transformer: "TypeTransformer") -> GuppyType:
        return transformer.transform(self) or self

    def __str__(self) -> str:
        return self.display_name

    def to_hugr(self) -> tys.Type:
        return tys.Variable(i=self.idx, b=self.hugr_bound())


@dataclass(frozen=True)
class ExistentialTypeVar(GuppyType):
    """Existential type variable, identified with a globally unique id.

    Is solved during type checking.
    """

    id: int
    display_name: str
    linear: bool = False

    name: ClassVar[Literal["ExistentialTypeVar"]] = "ExistentialTypeVar"

    _id_generator: ClassVar[Iterator[int]] = itertools.count()

    @classmethod
    def new(cls, display_name: str, linear: bool) -> "ExistentialTypeVar":
        return ExistentialTypeVar(next(cls._id_generator), display_name, linear)

    @staticmethod
    def build(*rgs: GuppyType, node: AstNode | None = None) -> GuppyType:
        raise NotImplementedError

    @property
    def type_args(self) -> Iterator["GuppyType"]:
        return iter(())

    def transform(self, transformer: "TypeTransformer") -> GuppyType:
        return transformer.transform(self) or self

    def __str__(self) -> str:
        return "?" + self.display_name

    def __hash__(self) -> int:
        return self.id

    def to_hugr(self) -> tys.Type:
        from guppylang.error import InternalGuppyError

        raise InternalGuppyError("Tried to convert free type variable to Hugr")


@dataclass(frozen=True)
class FunctionType(GuppyType):
    args: Sequence[GuppyType]
    returns: GuppyType
    arg_names: Sequence[str] | None = field(
        default=None,
        compare=False,  # Argument names are not taken into account for type equality
    )
    quantified: Sequence[BoundTypeVar] = field(default_factory=list)

    name: ClassVar[Literal["%function"]] = "%function"
    linear = False

    def __str__(self) -> str:
        prefix = (
            "forall " + ", ".join(str(v) for v in self.quantified) + ". "
            if self.quantified
            else ""
        )
        if len(self.args) == 1:
            [arg] = self.args
            return prefix + f"{arg} -> {self.returns}"
        else:
            return (
                prefix + f"({', '.join(str(a) for a in self.args)}) -> {self.returns}"
            )

    @staticmethod
    def build(*args: GuppyType, node: AstNode | None = None) -> GuppyType:
        # Function types cannot be constructed using `build`. The type parsing code
        # has a special case for function types.
        raise NotImplementedError

    @property
    def type_args(self) -> Iterator[GuppyType]:
        return itertools.chain(iter(self.args), iter((self.returns,)))

    def to_hugr(self) -> tys.PolyFuncType:
        ins = [t.to_hugr() for t in self.args]
        outs = [t.to_hugr() for t in type_to_row(self.returns)]
        func_ty = tys.FunctionType(input=ins, output=outs, extension_reqs=[])
        return tys.PolyFuncType(
            params=[tys.TypeTypeParam(b=v.hugr_bound()) for v in self.quantified],
            body=func_ty,
        )

    def hugr_bound(self) -> tys.TypeBound:
        # Functions are not equatable, only copyable
        return tys.TypeBound.Copyable

    def transform(self, transformer: "TypeTransformer") -> GuppyType:
        return transformer.transform(self) or FunctionType(
            [ty.transform(transformer) for ty in self.args],
            self.returns.transform(transformer),
            self.arg_names,
        )

    def instantiate(self, tys: Sequence[GuppyType]) -> "FunctionType":
        """Instantiates quantified type variables."""
        assert len(tys) == len(self.quantified)

        # Set the `preserve` flag for instantiated tuples and None
        preserved_tys: list[GuppyType] = []
        for ty in tys:
            if isinstance(ty, TupleType):
                ty = TupleType(ty.element_types, preserve=True)
            elif isinstance(ty, NoneType):
                ty = NoneType(preserve=True)
            preserved_tys.append(ty)

        inst = Instantiator(preserved_tys)
        return FunctionType(
            [ty.transform(inst) for ty in self.args],
            self.returns.transform(inst),
            self.arg_names,
        )

    def unquantified(self) -> tuple["FunctionType", Sequence[ExistentialTypeVar]]:
        """Replaces all quantified variables with free type variables."""
        inst = [
            ExistentialTypeVar.new(v.display_name, v.linear) for v in self.quantified
        ]
        return self.instantiate(inst), inst


@dataclass(frozen=True)
class TupleType(GuppyType):
    element_types: Sequence[GuppyType]

    # Flag to avoid turning the tuple into row when calling `type_to_row()`. This is
    # used to make sure that type vars instantiated to tuples are not broken up into
    # rows when generating a Hugr
    preserve: bool = field(default=False, compare=False)

    name: ClassVar[Literal["tuple"]] = "tuple"

    @staticmethod
    def build(*args: GuppyType, node: AstNode | None = None) -> GuppyType:
        from guppylang.error import GuppyError

        # TODO: Parse empty tuples via `tuple[()]`
        if len(args) == 0:
            raise GuppyError("Tuple type requires generic type arguments", node)
        return TupleType(list(args))

    def __str__(self) -> str:
        return f"({', '.join(str(e) for e in self.element_types)})"

    @property
    def linear(self) -> bool:
        return any(t.linear for t in self.element_types)

    @property
    def type_args(self) -> Iterator[GuppyType]:
        return iter(self.element_types)

    def to_hugr(self) -> tys.Type:
        ts = [t.to_hugr() for t in self.element_types]
        return tys.TupleType(inner=ts)

    def transform(self, transformer: "TypeTransformer") -> GuppyType:
        return transformer.transform(self) or TupleType(
            [ty.transform(transformer) for ty in self.element_types]
        )


@dataclass(frozen=True)
class SumType(GuppyType):
    element_types: Sequence[GuppyType]

    name: ClassVar[str] = "%tuple"

    @staticmethod
    def build(*args: GuppyType, node: AstNode | None = None) -> GuppyType:
        # Sum types cannot be parsed and constructed using `build` since they cannot be
        # written by the user
        raise NotImplementedError

    def __str__(self) -> str:
        return f"Sum({', '.join(str(e) for e in self.element_types)})"

    @property
    def linear(self) -> bool:
        return any(t.linear for t in self.element_types)

    @property
    def type_args(self) -> Iterator[GuppyType]:
        return iter(self.element_types)

    def to_hugr(self) -> tys.Type:
        if all(
            isinstance(e, TupleType) and len(e.element_types) == 0
            for e in self.element_types
        ):
            return tys.UnitSum(size=len(self.element_types))
        return tys.GeneralSum(row=[t.to_hugr() for t in self.element_types])

    def transform(self, transformer: "TypeTransformer") -> GuppyType:
        return transformer.transform(self) or SumType(
            [ty.transform(transformer) for ty in self.element_types]
        )


@dataclass(frozen=True)
class ListType(GuppyType):
    element_type: GuppyType

    name: ClassVar[Literal["list"]] = "list"
    linear: bool = field(default=False, init=False)

    @staticmethod
    def build(*args: GuppyType, node: AstNode | None = None) -> GuppyType:
        from guppylang.error import GuppyError

        if len(args) == 0:
            raise GuppyError("Missing type parameter for generic type `list`", node)
        if len(args) > 1:
            raise GuppyError("Too many type arguments for generic type `list`", node)
        (arg,) = args
        if arg.linear:
            raise GuppyError(
                "Type `list` cannot store linear data, use `linst` instead", node
            )
        return ListType(arg)

    def __str__(self) -> str:
        return f"list[{self.element_type}]"

    @property
    def type_args(self) -> Iterator[GuppyType]:
        return iter((self.element_type,))

    def to_hugr(self) -> tys.Type:
        return tys.Opaque(
            extension="Collections",
            id="List",
            args=[tys.TypeTypeArg(ty=self.element_type.to_hugr())],
            bound=self.hugr_bound(),
        )

    def transform(self, transformer: "TypeTransformer") -> GuppyType:
        return transformer.transform(self) or ListType(
            self.element_type.transform(transformer)
        )


@dataclass(frozen=True)
class LinstType(GuppyType):
    element_type: GuppyType

    name: ClassVar[Literal["linst"]] = "linst"

    @staticmethod
    def build(*args: GuppyType, node: AstNode | None = None) -> GuppyType:
        from guppylang.error import GuppyError

        if len(args) == 0:
            raise GuppyError("Missing type parameter for generic type `linst`", node)
        if len(args) > 1:
            raise GuppyError("Too many type arguments for generic type `linst`", node)
        return LinstType(args[0])

    def __str__(self) -> str:
        return f"linst[{self.element_type}]"

    @property
    def linear(self) -> bool:
        return self.element_type.linear

    @property
    def type_args(self) -> Iterator[GuppyType]:
        return iter((self.element_type,))

    def to_hugr(self) -> tys.Type:
        return tys.Opaque(
            extension="Collections",
            id="List",
            args=[tys.TypeTypeArg(ty=self.element_type.to_hugr())],
            bound=self.hugr_bound(),
        )

    def transform(self, transformer: "TypeTransformer") -> GuppyType:
        return transformer.transform(self) or LinstType(
            self.element_type.transform(transformer)
        )


@dataclass(frozen=True)
class NoneType(GuppyType):
    name: ClassVar[Literal["None"]] = "None"
    linear: bool = False

    # Flag to avoid turning the type into a row when calling `type_to_row()`. This is
    # used to make sure that type vars instantiated to Nones are not broken up into
    # empty rows when generating a Hugr
    preserve: bool = field(default=False, compare=False)

    @staticmethod
    def build(*args: GuppyType, node: AstNode | None = None) -> GuppyType:
        if len(args) > 0:
            from guppylang.error import GuppyError

            raise GuppyError("Type `None` is not generic", node)
        return NoneType()

    @property
    def type_args(self) -> Iterator[GuppyType]:
        return iter(())

    def substitute(self, s: Subst) -> GuppyType:
        return self

    def __str__(self) -> str:
        return "None"

    def to_hugr(self) -> tys.Type:
        return tys.TupleType(inner=[])

    def transform(self, transformer: "TypeTransformer") -> GuppyType:
        return transformer.transform(self) or self


@dataclass(frozen=True)
class BoolType(SumType):
    """The type of booleans."""

    linear: bool = False
    name: ClassVar[Literal["bool"]] = "bool"

    def __init__(self) -> None:
        # Hugr bools are encoded as Sum((), ())
        super().__init__([TupleType([]), TupleType([])])

    @staticmethod
    def build(*args: GuppyType, node: AstNode | None = None) -> GuppyType:
        if len(args) > 0:
            from guppylang.error import GuppyError

            raise GuppyError("Type `bool` is not generic", node)
        return BoolType()

    def __str__(self) -> str:
        return "bool"

    def transform(self, transformer: "TypeTransformer") -> GuppyType:
        return transformer.transform(self) or self


class TypeTransformer(ABC):
    """Abstract base class for a type visitor that transforms types."""

    @abstractmethod
    def transform(self, ty: GuppyType) -> GuppyType | None:
        """This method is called for each visited type.

        Return a transformed type or `None` to continue the recursive visit.
        """


class Substituter(TypeTransformer):
    """Type transformer that substitutes free type variables."""

    subst: Subst

    def __init__(self, subst: Subst) -> None:
        self.subst = subst

    def transform(self, ty: GuppyType) -> GuppyType | None:
        if isinstance(ty, ExistentialTypeVar):
            return self.subst.get(ty, None)
        return None


class Instantiator(TypeTransformer):
    """Type transformer that instantiates bound type variables."""

    tys: Sequence[GuppyType]

    def __init__(self, tys: Sequence[GuppyType]) -> None:
        self.tys = tys

    def transform(self, ty: GuppyType) -> GuppyType | None:
        if isinstance(ty, BoundTypeVar):
            # Instantiate if type for the index is available
            if ty.idx < len(self.tys):
                return self.tys[ty.idx]

            # Otherwise, lower the de Bruijn index
            return BoundTypeVar(ty.idx - len(self.tys), ty.display_name, ty.linear)
        return None


def unify(s: GuppyType, t: GuppyType, subst: Subst | None) -> Subst | None:
    """Computes a most general unifier for two types.

    Return a substitutions `subst` such that `s[subst] == t[subst]` or `None` if this
    not possible.
    """
    if subst is None:
        return None
    if s == t:
        return subst
    if isinstance(s, ExistentialTypeVar):
        return _unify_var(s, t, subst)
    if isinstance(t, ExistentialTypeVar):
        return _unify_var(t, s, subst)
    if type(s) == type(t):
        sargs, targs = list(s.type_args), list(t.type_args)
        if len(sargs) == len(targs):
            for sa, ta in zip(sargs, targs):
                subst = unify(sa, ta, subst)
            return subst
    return None


def _unify_var(var: ExistentialTypeVar, t: GuppyType, subst: Subst) -> Subst | None:
    """Helper function for unification of type variables."""
    if var in subst:
        return unify(subst[var], t, subst)
    if isinstance(t, ExistentialTypeVar) and t in subst:
        return unify(var, subst[t], subst)
    if var in t.unsolved_vars:
        return None
    return {var: t, **subst}


def type_from_ast(
    node: AstNode,
    globals: "Globals",
    type_var_mapping: dict[str, BoundTypeVar] | None = None,
) -> GuppyType:
    """Turns an AST expression into a Guppy type."""
    from guppylang.error import GuppyError

    if isinstance(node, ast.Name):
        x = node.id
        if x in globals.types:
            return globals.types[x].build(node=node)
        if x in globals.type_vars:
            if type_var_mapping is None:
                raise GuppyError(
                    "Free type variable. Only function types can be generic", node
                )
            var_decl = globals.type_vars[x]
            if var_decl.name not in type_var_mapping:
                type_var_mapping[var_decl.name] = BoundTypeVar(
                    len(type_var_mapping), var_decl.name, var_decl.linear
                )
            return type_var_mapping[var_decl.name]
        raise GuppyError("Unknown type", node)

    if isinstance(node, ast.Constant):
        v = node.value
        if v is None:
            return NoneType()
        if isinstance(v, str):
            try:
                [stmt] = ast.parse(v).body
                if not isinstance(stmt, ast.Expr):
                    raise GuppyError("Invalid Guppy type", node)
                return type_from_ast(stmt.value, globals, type_var_mapping)
            except (SyntaxError, ValueError):
                raise GuppyError("Invalid Guppy type", node) from None
        raise GuppyError(f"Constant `{v}` is not a valid type", node)

    if isinstance(node, ast.Tuple):
        return TupleType(
            [type_from_ast(el, globals, type_var_mapping) for el in node.elts]
        )

    if (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == "Callable"
        and isinstance(node.slice, ast.Tuple)
        and len(node.slice.elts) == 2
    ):
        # TODO: Do we want to allow polymorphic Callable types?
        [func_args, ret] = node.slice.elts
        if isinstance(func_args, ast.List):
            return FunctionType(
                [type_from_ast(a, globals, type_var_mapping) for a in func_args.elts],
                type_from_ast(ret, globals, type_var_mapping),
            )

    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
        x = node.value.id
        if x in globals.types:
            args = (
                node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
            )
            return globals.types[x].build(
                *(type_from_ast(a, globals, type_var_mapping) for a in args), node=node
            )

    raise GuppyError("Not a valid Guppy type", node)


def type_row_from_ast(node: ast.expr, globals: "Globals") -> Sequence[GuppyType]:
    """Turns an AST expression into a Guppy type row.

    This is needed to interpret the return type annotation of functions.
    """
    # The return type `-> None` is represented in the ast as `ast.Constant(value=None)`
    if isinstance(node, ast.Constant) and node.value is None:
        return []
    ty = type_from_ast(node, globals)
    if isinstance(ty, TupleType):
        return ty.element_types
    else:
        return [ty]


def row_to_type(row: Sequence[GuppyType]) -> GuppyType:
    """Turns a row of types into a single type by packing into a tuple."""
    if len(row) == 0:
        return NoneType()
    elif len(row) == 1:
        return row[0]
    else:
        return TupleType(row)


def type_to_row(ty: GuppyType) -> Sequence[GuppyType]:
    """Turns a type into a row of types by unpacking top-level tuples."""
    if isinstance(ty, NoneType) and not ty.preserve:
        return []
    if isinstance(ty, TupleType) and not ty.preserve:
        return ty.element_types
    return [ty]
