import ast
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Sequence, TYPE_CHECKING

import guppy.hugr.tys as tys
from guppy.ast_util import AstNode, set_location_from

if TYPE_CHECKING:
    from guppy.checker.core import Globals


class GuppyType(ABC):
    """Base class for all Guppy types.

    Note that all instances of `GuppyType` subclasses are expected to be immutable.
    """

    name: str = ""

    @staticmethod
    @abstractmethod
    def build(*args: "GuppyType", node: Optional[AstNode] = None) -> "GuppyType":
        pass

    @property
    @abstractmethod
    def linear(self) -> bool:
        pass

    @abstractmethod
    def to_hugr(self) -> tys.SimpleType:
        pass


@dataclass(frozen=True)
class FunctionType(GuppyType):
    args: Sequence[GuppyType]
    returns: GuppyType
    arg_names: Optional[Sequence[str]] = field(
        default=None,
        compare=False,  # Argument names are not taken into account for type equality
    )

    name: str = "->"
    linear = False

    def __str__(self) -> str:
        if len(self.args) == 1:
            [arg] = self.args
            return f"{arg} -> {self.returns}"
        else:
            return f"({', '.join(str(a) for a in self.args)}) -> {self.returns}"

    @staticmethod
    def build(*args: GuppyType, node: Optional[AstNode] = None) -> GuppyType:
        # Function types cannot be constructed using `build`. The type parsing code
        # has a special case for function types.
        raise NotImplementedError()

    def to_hugr(self) -> tys.SimpleType:
        ins = [t.to_hugr() for t in self.args]
        outs = [t.to_hugr() for t in type_to_row(self.returns)]
        return tys.FunctionType(input=ins, output=outs, extension_reqs=[])


@dataclass(frozen=True)
class TupleType(GuppyType):
    element_types: Sequence[GuppyType]

    name: str = "tuple"

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

    def to_hugr(self) -> tys.SimpleType:
        ts = [t.to_hugr() for t in self.element_types]
        return tys.Tuple(inner=ts)


@dataclass(frozen=True)
class SumType(GuppyType):
    element_types: Sequence[GuppyType]

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

    def to_hugr(self) -> tys.SimpleType:
        if all(
            isinstance(e, TupleType) and len(e.element_types) == 0
            for e in self.element_types
        ):
            return tys.UnitSum(size=len(self.element_types))
        return tys.GeneralSum(row=[t.to_hugr() for t in self.element_types])


@dataclass(frozen=True)
class NoneType(GuppyType):
    name: str = "None"
    linear: bool = False

    @staticmethod
    def build(*args: GuppyType, node: Optional[AstNode] = None) -> GuppyType:
        if len(args) > 0:
            from guppy.error import GuppyError

            raise GuppyError("Type `None` is not generic", node)
        return NoneType()

    def __str__(self) -> str:
        return "None"

    def to_hugr(self) -> tys.SimpleType:
        return tys.Tuple(inner=[])


@dataclass(frozen=True)
class BoolType(SumType):
    """The type of booleans."""

    linear = False
    name = "bool"

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


def _lookup_type(node: AstNode, globals: "Globals") -> Optional[type[GuppyType]]:
    if isinstance(node, ast.Name) and node.id in globals.types:
        return globals.types[node.id]
    if isinstance(node, ast.Constant) and node.value is None:
        return NoneType
    if (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value in globals.types
    ):
        return globals.types[node.value]
    return None


def type_from_ast(node: AstNode, globals: "Globals") -> GuppyType:
    """Turns an AST expression into a Guppy type."""
    if isinstance(node, ast.Name) and (ty := _lookup_type(node, globals)):
        return ty.build(node=node)
    if isinstance(node, ast.Constant) and (ty := _lookup_type(node, globals)):
        name = ast.Name(id=node.value)
        set_location_from(name, node)
        return ty.build(node=name)
    if isinstance(node, ast.Subscript) and (ty := _lookup_type(node.value, globals)):
        args = node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
        return ty.build(*(type_from_ast(a, globals) for a in args), node=node)
    if isinstance(node, ast.Tuple):
        return TupleType([type_from_ast(el, globals) for el in node.elts])
    if (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == "Callable"
        and isinstance(node.slice, ast.Tuple)
        and len(node.slice.elts) == 2
    ):
        [func_args, ret] = node.slice.elts
        if isinstance(func_args, ast.List):
            return FunctionType(
                [type_from_ast(a, globals) for a in func_args.elts],
                type_from_ast(ret, globals),
            )
    from guppy.error import GuppyError

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
