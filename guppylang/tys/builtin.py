from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from hugr.serialization import tys

from guppylang.ast_util import AstNode
from guppylang.definition.common import DefId
from guppylang.definition.ty import FlaggedArgs, OpaqueTypeDef, TypeDef, check_no_flags
from guppylang.error import GuppyError
from guppylang.tys.arg import Argument, ConstArg, TypeArg
from guppylang.tys.param import ConstParam, TypeParam
from guppylang.tys.ty import (
    FuncInput,
    FunctionType,
    InputFlags,
    NoneType,
    NumericType,
    OpaqueType,
    TupleType,
    Type,
)

if TYPE_CHECKING:
    from guppylang.checker.core import Globals


@dataclass(frozen=True)
class _CallableTypeDef(TypeDef):
    """Type definition associated with the builtin `Callable` type.

    Any impls on functions can be registered with this definition.
    """

    name: Literal["Callable"] = field(default="Callable", init=False)

    def check_instantiate(
        self, args: FlaggedArgs, globals: "Globals", loc: AstNode | None = None
    ) -> FunctionType:
        # We get the inputs/output as a flattened list: `args = [*inputs, output]`.
        if not args:
            raise GuppyError(f"Missing parameter for type `{self.name}`", loc)
        args = [
            # TODO: Better error location
            (TypeParam(0, f"T{i}", can_be_linear=True).check_arg(arg, loc).ty, flags)
            for i, (arg, flags) in enumerate(args)
        ]
        *inputs, (output_ty, output_flags) = args
        for ty, flags in inputs:
            if InputFlags.Inout in flags and not ty.linear:
                raise GuppyError(
                    f"Non-linear type `{ty}` cannot be annotated as `@inout`",
                    loc,  # TODO: Better error location
                )
        if output_flags != InputFlags.NoFlags:
            raise GuppyError(
                "`@` type annotations are not allowed in this position", loc
            )
        return FunctionType([FuncInput(ty, flags) for ty, flags in inputs], output_ty)


@dataclass(frozen=True)
class _TupleTypeDef(TypeDef):
    """Type definition associated with the builtin `tuple` type.

    Any impls on tuples can be registered with this definition.
    """

    name: Literal["tuple"] = field(default="tuple", init=False)

    def check_instantiate(
        self, args: FlaggedArgs, globals: "Globals", loc: AstNode | None = None
    ) -> TupleType:
        args = check_no_flags(args, loc)
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

    name: Literal["None"] = field(default="None", init=False)

    def check_instantiate(
        self, args: FlaggedArgs, globals: "Globals", loc: AstNode | None = None
    ) -> NoneType:
        if args:
            raise GuppyError("Type `None` is not parameterized", loc)
        return NoneType()


@dataclass(frozen=True)
class _NumericTypeDef(TypeDef):
    """Type definition associated with the builtin numeric types.

    Any impls on numerics can be registered with these definitions.
    """

    ty: NumericType

    def check_instantiate(
        self, args: FlaggedArgs, globals: "Globals", loc: AstNode | None = None
    ) -> NumericType:
        if args:
            raise GuppyError(f"Type `{self.name}` is not parameterized", loc)
        return self.ty


@dataclass(frozen=True)
class _ListTypeDef(OpaqueTypeDef):
    """Type definition associated with the builtin `list` type.

    We have a custom definition to give a nicer error message if the user tries to put
    linear data into a regular list.
    """

    def check_instantiate(
        self, args: FlaggedArgs, globals: "Globals", loc: AstNode | None = None
    ) -> OpaqueType:
        if len(args) == 1:
            [arg] = check_no_flags(args, loc)
            if isinstance(arg, TypeArg) and arg.ty.linear:
                raise GuppyError(
                    "Type `list` cannot store linear data, use `linst` instead", loc
                )
        return super().check_instantiate(args, globals, loc)


def _list_to_hugr(args: Sequence[Argument]) -> tys.Type:
    # Type checker ensures that we get a single arg of kind type
    [arg] = args
    assert isinstance(arg, TypeArg)
    ty = tys.Opaque(
        extension="Collections",
        id="List",
        args=[arg.to_hugr()],
        bound=arg.ty.hugr_bound,
    )
    return tys.Type(ty)


def _array_to_hugr(args: Sequence[Argument]) -> tys.Type:
    # Type checker ensures that we get a two args
    [ty_arg, len_arg] = args
    assert isinstance(ty_arg, TypeArg)
    assert isinstance(len_arg, ConstArg)
    ty = tys.Opaque(
        extension="prelude",
        id="array",
        args=[len_arg.to_hugr(), ty_arg.to_hugr()],
        bound=ty_arg.ty.hugr_bound,
    )
    return tys.Type(ty)


callable_type_def = _CallableTypeDef(DefId.fresh(), None)
tuple_type_def = _TupleTypeDef(DefId.fresh(), None)
none_type_def = _NoneTypeDef(DefId.fresh(), None)
bool_type_def = OpaqueTypeDef(
    id=DefId.fresh(),
    name="bool",
    defined_at=None,
    params=[],
    always_linear=False,
    to_hugr=lambda _: tys.Type(tys.SumType(tys.UnitSum(size=2))),
)
nat_type_def = _NumericTypeDef(
    DefId.fresh(), "nat", None, NumericType(NumericType.Kind.Nat)
)
int_type_def = _NumericTypeDef(
    DefId.fresh(), "int", None, NumericType(NumericType.Kind.Int)
)
float_type_def = _NumericTypeDef(
    DefId.fresh(), "float", None, NumericType(NumericType.Kind.Float)
)
linst_type_def = OpaqueTypeDef(
    id=DefId.fresh(),
    name="linst",
    defined_at=None,
    params=[TypeParam(0, "T", can_be_linear=True)],
    always_linear=False,
    to_hugr=_list_to_hugr,
)
list_type_def = _ListTypeDef(
    id=DefId.fresh(),
    name="list",
    defined_at=None,
    params=[TypeParam(0, "T", can_be_linear=False)],
    always_linear=False,
    to_hugr=_list_to_hugr,
)
array_type_def = OpaqueTypeDef(
    id=DefId.fresh(),
    name="array",
    defined_at=None,
    params=[
        TypeParam(0, "T", can_be_linear=True),
        ConstParam(1, "n", NumericType(NumericType.Kind.Nat)),
    ],
    always_linear=False,
    to_hugr=_array_to_hugr,
)


def bool_type() -> OpaqueType:
    return OpaqueType([], bool_type_def)


def int_type() -> NumericType:
    return NumericType(NumericType.Kind.Int)


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
    assert isinstance(ty, OpaqueType)
    assert ty.defn in (list_type_def, linst_type_def)
    (arg,) = ty.args
    assert isinstance(arg, TypeArg)
    return arg.ty
