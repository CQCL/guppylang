import ast
import functools
import itertools
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Sequence, TYPE_CHECKING, Mapping, Iterator, ClassVar, \
    Literal

import guppy.hugr.tys as tys
from guppy.ast_util import AstNode, set_location_from

if TYPE_CHECKING:
    from guppy.checker.core import Globals


@dataclass(frozen=True)
class TypeVarId:
    """Identifier for free type variables."""
    id: int

    _id_generator: ClassVar[Iterator[int]] = itertools.count()

    @classmethod
    def new(cls) -> "TypeVarId":
        return TypeVarId(next(cls._id_generator))


Subst = dict[TypeVarId, "GuppyType"]
Inst = Sequence["GuppyType"]


@dataclass(frozen=True)
class GuppyType(ABC):
    """Base class for all Guppy types.

    Note that all instances of `GuppyType` subclasses are expected to be immutable.
    """

    name: ClassVar[str]

    # Cache for free variables
    _free_vars: Mapping["TypeVarId", "FreeTypeVar"] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        # Make sure that we don't have higher-rank polymorphic types
        for arg in self.type_args:
            if isinstance(arg, FunctionType) and arg.quantified:
                from guppy.error import InternalGuppyError

                raise InternalGuppyError(
                    "Tried to construct a higher-rank polymorphic type!"
                )

        # Compute free variables
        if isinstance(self, FreeTypeVar):
            vs = {self.id: self}
        else:
            vs: dict[TypeVarId, FreeTypeVar] = {}
            for arg in self.type_args:
                vs |= arg.free_vars
        object.__setattr__(self, "_free_vars", vs)

    @staticmethod
    @abstractmethod
    def build(*args: "GuppyType", node: Optional[AstNode] = None) -> "GuppyType":
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
    def to_hugr(self) -> tys.SimpleType:
        pass

    @abstractmethod
    def transform(self, transformer: "TypeTransformer") -> "GuppyType":
        pass

    @property
    def free_vars(self) -> Mapping["TypeVarId", "FreeTypeVar"]:
        return self._free_vars

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
    def build(*rgs: GuppyType, node: Optional[AstNode] = None) -> GuppyType:
        raise NotImplementedError()

    @property
    def type_args(self) -> Iterator["GuppyType"]:
        return iter(())

    def transform(self, transformer: "TypeTransformer") -> GuppyType:
        return transformer.transform(self) or self

    def __str__(self) -> str:
        return self.display_name

    def to_hugr(self) -> tys.SimpleType:
        # TODO
        return NoneType().to_hugr()


@dataclass(frozen=True)
class FreeTypeVar(GuppyType):
    """Free type variable, identified with a globally unique id."""

    id: TypeVarId
    display_name: str
    linear: bool = False

    name: ClassVar[Literal["FreeTypeVar"]] = "FreeTypeVar"

    @staticmethod
    def build(*rgs: GuppyType, node: Optional[AstNode] = None) -> GuppyType:
        raise NotImplementedError()

    @property
    def type_args(self) -> Iterator["GuppyType"]:
        return iter(())

    def transform(self, transformer: "TypeTransformer") -> GuppyType:
        return transformer.transform(self) or self

    def __str__(self) -> str:
        return "?" + self.display_name

    def to_hugr(self) -> tys.SimpleType:
        from guppy.error import InternalGuppyError

        raise InternalGuppyError("Tried to convert free type variable to Hugr")


@dataclass(frozen=True)
class FunctionType(GuppyType):
    args: Sequence[GuppyType]
    returns: GuppyType
    arg_names: Optional[Sequence[str]] = field(
        default=None,
        compare=False,  # Argument names are not taken into account for type equality
    )
    quantified: Sequence[BoundTypeVar] = field(default_factory=list)

    name: ClassVar[Literal["%function"]] = "%function"
    linear = False

    def __str__(self) -> str:
        prefix = "forall " + ", ".join(str(v) for v in self.quantified) + ". " if self.quantified else ""
        if len(self.args) == 1:
            [arg] = self.args
            return prefix + f"{arg} -> {self.returns}"
        else:
            return prefix + f"({', '.join(str(a) for a in self.args)}) -> {self.returns}"

    @staticmethod
    def build(*args: GuppyType, node: Optional[AstNode] = None) -> GuppyType:
        # Function types cannot be constructed using `build`. The type parsing code
        # has a special case for function types.
        raise NotImplementedError()

    @property
    def type_args(self) -> Iterator[GuppyType]:
        return itertools.chain(iter(self.args), iter((self.returns,)))

    def to_hugr(self) -> tys.SimpleType:
        ins = [t.to_hugr() for t in self.args]
        outs = [t.to_hugr() for t in type_to_row(self.returns)]
        return tys.FunctionType(input=ins, output=outs, extension_reqs=[])

    def transform(self, transformer: "TypeTransformer") -> GuppyType:
        return transformer.transform(self) or FunctionType(
            [ty.transform(transformer) for ty in self.args],
            self.returns.transform(transformer),
            self.arg_names
        )

    def instantiate(self, tys: Sequence[GuppyType]) -> "FunctionType":
        """Instantiates quantified type variables."""
        assert len(tys) == len(self.quantified)
        inst = Instantiator(tys)
        return FunctionType(
            [ty.transform(inst) for ty in self.args],
            self.returns.transform(inst),
            self.arg_names,
        )

    def unquantified(self) -> tuple["FunctionType", Sequence[FreeTypeVar]]:
        """Replaces all quantified variables with free type variables."""
        inst = [
            FreeTypeVar(TypeVarId.new(), v.display_name, v.linear)
            for v in self.quantified
        ]
        return self.instantiate(inst), inst


@dataclass(frozen=True)
class TupleType(GuppyType):
    element_types: Sequence[GuppyType]

    name: ClassVar[Literal["tuple"]] = "tuple"

    @staticmethod
    def build(*args: GuppyType, node: Optional[AstNode] = None) -> GuppyType:
        from guppy.error import GuppyError

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

    def substitute(self, s: Subst) -> GuppyType:
        return TupleType([ty.substitute(s) for ty in self.element_types])

    def to_hugr(self) -> tys.SimpleType:
        ts = [t.to_hugr() for t in self.element_types]
        return tys.Tuple(inner=ts)

    def transform(self, transformer: "TypeTransformer") -> GuppyType:
        return transformer.transform(self) or TupleType(
            [ty.transform(transformer) for ty in self.element_types]
        )


@dataclass(frozen=True)
class SumType(GuppyType):
    element_types: Sequence[GuppyType]

    name: ClassVar[str] = "%tuple"

    @staticmethod
    def build(*args: GuppyType, node: Optional[AstNode] = None) -> GuppyType:
        # Sum types cannot be parsed and constructed using `build` since they cannot be
        # written by the user
        raise NotImplementedError()

    def __str__(self) -> str:
        return f"Sum({', '.join(str(e) for e in self.element_types)})"

    @property
    def linear(self) -> bool:
        return any(t.linear for t in self.element_types)

    @property
    def type_args(self) -> Iterator[GuppyType]:
        return iter(self.element_types)

    def substitute(self, s: Subst) -> GuppyType:
        return TupleType([ty.substitute(s) for ty in self.element_types])

    def to_hugr(self) -> tys.SimpleType:
        if all(
            isinstance(e, TupleType) and len(e.element_types) == 0
            for e in self.element_types
        ):
            return tys.UnitSum(size=len(self.element_types))
        return tys.GeneralSum(row=[t.to_hugr() for t in self.element_types])

    def transform(self, transformer: "TypeTransformer") -> GuppyType:
        return transformer.transform(self) or TupleType(
            [ty.transform(transformer) for ty in self.element_types]
        )


@dataclass(frozen=True)
class NoneType(GuppyType):
    name: ClassVar[Literal["None"]] = "None"
    linear: bool = False

    @staticmethod
    def build(*args: GuppyType, node: Optional[AstNode] = None) -> GuppyType:
        if len(args) > 0:
            from guppy.error import GuppyError

            raise GuppyError("Type `None` is not generic", node)
        return NoneType()

    @property
    def type_args(self) -> Iterator[GuppyType]:
        return iter(())

    def substitute(self, s: Subst) -> GuppyType:
        return self

    def __str__(self) -> str:
        return "None"

    def to_hugr(self) -> tys.SimpleType:
        return tys.Tuple(inner=[])

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
    def build(*args: GuppyType, node: Optional[AstNode] = None) -> GuppyType:
        if len(args) > 0:
            from guppy.error import GuppyError

            raise GuppyError("Type `bool` is not generic", node)
        return BoolType()

    def __str__(self) -> str:
        return "bool"

    def transform(self, transformer: "TypeTransformer") -> GuppyType:
        return transformer.transform(self) or self


class TypeTransformer(ABC):
    """Abstract base class for a type visitor that transforms types."""

    @abstractmethod
    def transform(self, ty: GuppyType) -> Optional[GuppyType]:
        """This method is called for each visited type.

        Return a transformed type or `None` to continue the recursive visit.
        """
        pass


class Substituter(TypeTransformer):
    """Type transformer that substitutes free type variables."""

    subst: Subst

    def __init__(self, subst: Subst) -> None:
        self.subst = subst

    def transform(self, ty: GuppyType) -> Optional[GuppyType]:
        if isinstance(ty, FreeTypeVar):
            return self.subst.get(ty.id, None)
        return None


class Instantiator(TypeTransformer):
    """Type transformer that instantiates bound type variables."""

    tys: Sequence[GuppyType]

    def __init__(self, tys: Sequence[GuppyType]) -> None:
        self.tys = tys

    def transform(self, ty: GuppyType) -> Optional[GuppyType]:
        if isinstance(ty, BoundTypeVar):
            # Instantiate if type for the index is available
            if ty.idx < len(self.tys):
                return self.tys[ty.idx]

            # Otherwise, lower the de Bruijn index
            return BoundTypeVar(ty.idx - len(self.tys), ty.display_name, ty.linear)
        return None


def unify(s: GuppyType, t: GuppyType, subst: Optional[Subst]) -> Optional[Subst]:
    """Computes a most general unifier for two types.

    Return a substitutions `subst` such that `s[subst] == t[subst]` or `None` if this
    not possible.
    """
    if subst is None:
        return None
    if s == t:
        return subst
    if isinstance(s, FreeTypeVar):
        return _unify_var(s, t, subst)
    if isinstance(t, FreeTypeVar):
        return _unify_var(t, s, subst)
    if type(s) == type(t):
        sargs, targs = list(s.type_args), list(t.type_args)
        if len(sargs) == len(targs):
            for sa, ta in zip(sargs, targs):
                subst = unify(sa, ta, subst)
            return subst
    return None


def _unify_var(var: FreeTypeVar, t: GuppyType, subst: Subst) -> Optional[Subst]:
    """Helper function for unification of type variables."""
    if var.id in subst:
        return unify(subst[var.id], t, subst)
    if isinstance(t, FreeTypeVar) and t.id in subst:
        return unify(var, subst[t.id], subst)
    if var.id in t.free_vars:
        return None
    return {var.id: t, **subst}


def type_from_ast(node: AstNode, globals: "Globals", type_var_mapping: Optional[dict[str, BoundTypeVar]] = None) -> GuppyType:
    """Turns an AST expression into a Guppy type."""
    from guppy.error import GuppyError

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
                return type_from_ast(ast.parse(v), globals, type_var_mapping)
            except Exception:
                raise GuppyError("Invalid Guppy type", node)
        raise GuppyError(f"Constant `{v}` is not a valid type", node)

    if isinstance(node, ast.Tuple):
        return TupleType([type_from_ast(el, globals) for el in node.elts])

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
            args = node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
            return globals.types[x].build(*(type_from_ast(a, globals) for a in args), node=node)

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
    if isinstance(ty, NoneType):
        return []
    if isinstance(ty, TupleType):
        return ty.element_types
    return [ty]
