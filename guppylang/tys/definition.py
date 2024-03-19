from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Sequence, Callable, Literal
from typing_extensions import assert_never

from guppylang.ast_util import AstNode
from guppylang.error import GuppyError
from guppylang.hugr import tys
from guppylang.tys.arg import Argument, ConstArg, TypeArg
from guppylang.tys.param import Parameter, TypeParam

from guppylang.tys.ty import Type, OpaqueType, TupleType, NoneType, FunctionType


@dataclass(frozen=True)
class TypeDef(ABC):
    """Abstract base class for type definitions."""

    name: str

    @abstractmethod
    def check_instantiate(self, args: Sequence[Argument], loc: AstNode | None = None) -> Type:
        """Checks if the type definition can be instantiated with the given arguments.

        Returns the resulting concrete type or raises a user error if the arguments are
        invalid.
        """


@dataclass(frozen=True)
class OpaqueTypeDef(TypeDef):
    """An opaque type definition that is backed by some Hugr type."""

    params: Sequence[Parameter]
    always_linear: bool
    to_hugr: Callable[[Sequence[Argument]], tys.Type]
    bound: tys.TypeBound | None = None

    def check_instantiate(self, args: Sequence[Argument], loc: AstNode | None = None) -> OpaqueType:
        """Checks if the type definition can be instantiated with the given arguments.

        Returns the resulting concrete type or raises a user error if the arguments are
        invalid.
        """
        exp, act = len(self.params), len(args)
        if exp > act:
            raise GuppyError(f"Missing parameter for type `{self.name}`", loc)
        elif 0 == exp < act:
            raise GuppyError(f"Type `{self.name}` is not parameterized", loc)
        elif 0 < exp < act:
            raise GuppyError(f"Too many parameters for type `{self.name}`", loc)

        # Now check that the kinds match up
        for param, arg in zip(self.params, args, strict=True):
            # TODO: The error location is bad. We want the location of `arg`, not of the
            #  whole thing.
            param.check_arg(arg, loc)
        return OpaqueType(args, self)


@dataclass(frozen=True)
class _CallableTypeDef(TypeDef):
    """Type definition associated with the builtin `Callable` type.

    Any impls on functions can be registered with this definition.
    """

    name: Literal["Callable"] = field(default="Callable", init=False)

    def check_instantiate(self, args: Sequence[Argument], loc: AstNode | None = None) -> FunctionType:
        # We get the inputs/output as a flattened list: `args = [*inputs, output]`.
        if not args:
            raise GuppyError(f"Missing parameter for type `{self.name}`", loc)
        args = [
            # TODO: Better error location
            TypeParam(0, f"T{i}", can_be_linear=True).check_arg(arg, loc).ty
            for i, arg in enumerate(args)
        ]
        *inputs, output = args
        return FunctionType(inputs, output)


@dataclass(frozen=True)
class _TupleTypeDef(TypeDef):
    """Type definition associated with the builtin `tuple` type.

    Any impls on tuples can be registered with this definition.
    """

    name: Literal["tuple"] = field(default="tuple", init=False)

    def check_instantiate(self, args: Sequence[Argument], loc: AstNode | None = None) -> TupleType:
        # We accept any number of arguments. If users just write `tuple`, we give them
        # the empty tuple type. We just have to make sure that the args are of kind type
        args = [
            # TODO: Better error location
            TypeParam(0, f"T{i}", can_be_linear=True).check_arg(arg, loc).ty
            for i, arg in enumerate(args)
        ]
        return TupleType(args)


@dataclass(frozen=True)
class _NoneTypeDef(TypeDef):
    """Type definition associated with the builtin `None` type.

    Any impls on None can be registered with this definition.
    """

    name: Literal["tuple"] = field(default="tuple", init=False)

    def check_instantiate(self, args: Sequence[Argument], loc: AstNode | None = None) -> NoneType:
        if args:
            raise GuppyError(f"Type `None` is not parameterized", loc)
        return NoneType()


@dataclass(frozen=True)
class _ListTypeDef(OpaqueTypeDef):
    """Type definition associated with the builtin `list` type.

    We have a custom definition to give a nicer error message if the user tries to put
    linear data into a regular list.
    """

    def check_instantiate(self, args: Sequence[Argument], loc: AstNode | None = None) -> OpaqueType:
        if len(args) == 1:
            [arg] = args
            if isinstance(arg, TypeArg) and arg.ty.linear:
                raise GuppyError(
                    "Type `list` cannot store linear data, use `linst` instead", loc
                )
        return super().check_instantiate(args, loc)


def _list_to_hugr(args: Sequence[Argument]) -> tys.Opaque:
    return tys.Opaque(
        extension="Collections",
        id="List",
        args=[arg.to_hugr() for arg in args],
        bound=tys.TypeBound.join(
            *(arg.ty.hugr_bound for arg in args if isinstance(arg, TypeArg))
        ),
    )


callable_type_def = _CallableTypeDef()
tuple_type_def = _TupleTypeDef()
none_type_def = _NoneTypeDef()
bool_type_def = OpaqueTypeDef(
    name="bool",
    params=[],
    always_linear=False,
    to_hugr=lambda _: tys.UnitSum(size=2),
)
linst_type_def = OpaqueTypeDef(
    name="linst",
    params=[TypeParam(0, "T", can_be_linear=True)],
    always_linear=False,
    to_hugr=_list_to_hugr
)
list_type_def = _ListTypeDef(
    name="list",
    params=[TypeParam(0, "T", can_be_linear=False)],
    always_linear=False,
    to_hugr=_list_to_hugr
)


def bool_type() -> OpaqueType:
    return OpaqueType([], bool_type_def)


def list_type(element_ty: Type) -> OpaqueType:
    return OpaqueType([TypeArg(element_ty)], list_type_def)


def linst_type(element_ty: Type) -> OpaqueType:
    return OpaqueType([TypeArg(element_ty)], linst_type_def)


def is_bool_type(ty: Type) -> bool:
    return isinstance(ty, OpaqueType) and ty.defn == bool_type_def


def is_list_type(ty: Type) -> bool:
    return isinstance(ty, OpaqueType) and ty.defn == list_type_def


def is_linst_type(ty: Type) -> bool:
    return isinstance(ty, OpaqueType) and ty.defn == linst_type_def


def get_element_type(ty: Type) -> Type:
    assert isinstance(ty, OpaqueType) and ty.defn in (list_type_def, linst_type_def)
    arg, = ty.args
    assert isinstance(arg, TypeArg)
    return arg.ty



