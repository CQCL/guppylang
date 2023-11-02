import ast
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Any, Sequence, Mapping, TYPE_CHECKING, Union

import guppy.hugr.tys as tys
from guppy.ast_util import AstNode, set_location_from

if TYPE_CHECKING:
    from guppy.compiler_base import Globals


class GuppyType(ABC):
    """Base class for all Guppy types.

    Note that all instances of `GuppyType` subclasses are expected to be immutable.
    """

    name: str = ""

    @staticmethod
    @abstractmethod
    def build(*args: "GuppyType", node: Union[ast.Name, ast.Subscript]) -> "GuppyType":
        pass

    @property
    @abstractmethod
    def linear(self) -> bool:
        pass

    @abstractmethod
    def to_hugr(self) -> tys.SimpleType:
        pass


@dataclass(frozen=True)
class TypeRow:
    tys: Sequence[GuppyType]

    def __str__(self) -> str:
        if len(self.tys) == 0:
            return "None"
        elif len(self.tys) == 1:
            return str(self.tys[0])
        else:
            return f"({', '.join(str(e) for e in self.tys)})"


@dataclass(frozen=True)
class FunctionType(GuppyType):
    args: Sequence[GuppyType]
    returns: Sequence[GuppyType]
    arg_names: Optional[Sequence[str]] = field(
        default=None,
        compare=False,  # Argument names are not taken into account for type equality
    )

    name: str = "->"
    linear = False

    def __str__(self) -> str:
        return f"{TypeRow(self.args)} -> {TypeRow(self.returns)}"

    @staticmethod
    def build(*args: GuppyType, node: Union[ast.Name, ast.Subscript]) -> GuppyType:
        # Function types cannot be constructed using `build`. The type parsing code
        # has a special case for function types.
        raise NotImplementedError()

    def to_hugr(self) -> tys.SimpleType:
        ins = [t.to_hugr() for t in self.args]
        outs = [t.to_hugr() for t in self.returns]
        return tys.FunctionType(input=ins, output=outs, extension_reqs=[])


@dataclass(frozen=True)
class TupleType(GuppyType):
    element_types: Sequence[GuppyType]

    name: str = "tuple"

    @staticmethod
    def build(*args: GuppyType, node: Union[ast.Name, ast.Subscript]) -> GuppyType:
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
    def build(*args: GuppyType, node: Union[ast.Name, ast.Subscript]) -> GuppyType:
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


def _lookup_type(node: AstNode, globals: "Globals") -> Optional[type[GuppyType]]:
    if isinstance(node, ast.Name) and node.id in globals.types:
        return globals.types[node.id]
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
                type_row_from_ast(ret, globals).tys,
            )
    from guppy.error import GuppyError

    raise GuppyError("Not a valid Guppy type", node)


def type_row_from_ast(node: ast.expr, globals: "Globals") -> TypeRow:
    """Turns an AST expression into a Guppy type row.

    This is needed to interpret the return type annotation of functions.
    """
    # The return type `-> None` is represented in the ast as `ast.Constant(value=None)`
    if isinstance(node, ast.Constant) and node.value is None:
        return TypeRow([])
    ty = type_from_ast(node, globals)
    if isinstance(ty, TupleType):
        return TypeRow(ty.element_types)
    else:
        return TypeRow([ty])
