from abc import ABC
from dataclasses import replace, dataclass
from types import NoneType

from typing import assert_never, cast, Mapping, TypeAlias, Sequence

from guppylang_internals.definition.common import DefId
from guppylang_internals.definition.protocol import CheckedProtocolDef
from guppylang_internals.definition.ty import TypeDef
from guppylang_internals.definition.value import CallableDef
from guppylang_internals.engine import DEF_STORE, ENGINE
from guppylang_internals.tys.arg import Argument
from guppylang_internals.tys.protocol import ProtocolInst
from guppylang_internals.tys.subst import Subst, Inst
from guppylang_internals.tys.ty import BoundTypeVar, ExistentialTypeVar, FunctionType, NumericType, OpaqueType, StructType, SumType, TupleType, Type, unify
from guppylang_internals.tys.builtin import (
    callable_type_def,
    float_type_def,
    int_type_def,
    nat_type_def,
    none_type_def,
    tuple_type_def,
)


@dataclass(frozen=True)
class ImplProofBase(ABC):
    proto: ProtocolInst
    ty: Type

    def __post_init__(self) -> None:
        assert all(not arg.unsolved_vars for arg in self.proto.type_args)


@dataclass(frozen=True)
class ConcreteImplProof(ImplProofBase):
    #: For each protocol member, the concrete function that implements it together with
    #: an instantiation of the type parameters of the implementation. This could refer
    #: to bound variables specified by the protocol method.
    #: If we have a protocol `def foo[T](x: T, y: int)` and implementation
    #: `def foo[A, B](x: A, y: B)`, then the instantiation will specify `A := T` and
    #: `B := int`.
    member_impls: Mapping[str, tuple[DefId, Inst]]

    # def __post_init__(self) -> None:
    #     assert self.member_impls.keys() == self.proto.


@dataclass(frozen=True)
class AssumptionImplProof(ImplProofBase):
    ty: BoundTypeVar

    def __post_init__(self) -> None:
        super().__post_init__()
        assert self.proto in self.ty.implements


ImplProof: TypeAlias = ConcreteImplProof | AssumptionImplProof


def unify_args(xs: Sequence[Argument], ys: Sequence[Argument], subst: Subst) -> Subst | None:
    for x, y in zip(xs, ys, strict=True):
        subst = unify(x, y, subst)
        if subst is None:
            return None
    return subst


def check_protocol(ty: Type, protocol: ProtocolInst) -> tuple[ImplProof, Subst]:
    # Invariant: ty and protocol might have unsolved variables
    protocol_def = ENGINE.get_checked(protocol.definition)
    assert isinstance(protocol_def, CheckedProtocolDef)

    if isinstance(ty, BoundTypeVar):
        candidates = []
        for impl in ty.implements:
            if impl.definition == protocol.definition:
                subst = unify_args(protocol.type_args, impl.type_args, {})
                if subst is not None:
                    candidates.append((impl, subst))
        if len(candidates) != 1:
            raise "Zero or more than one"
        [(_, subst)] = candidates
        return AssumptionImplProof(protocol.substitute(subst), ty.substitute(subst)), subst

    subst: Subst | None = {}
    member_impls = {}
    for name, proto_sig in protocol_def.members.items():
        # Partially instantiate proto_sig with `protocol.type_args` and `ty`

        func = get_instance_func(ty, name)
        if not func:
            raise "Missing member implementation"
        impl_sig, impl_vars = func.ty.unquantified()
        # TODO Make this a method
        # proto_sig_params = proto_sig.params
        proto_sig = replace(proto_sig, params=[])
        subst = unify(proto_sig, impl_sig, subst)
        if subst is None:
            raise "Signature Mismatch"
        if any(x not in subst for x in impl_vars):
            raise ""
        member_impls[name] = (func.id, [subst[x] for x in impl_vars])

    if any(x not in subst for arg in protocol.type_args for x in arg.unsolved_vars):
        raise "Couldn't figure out variables in protocol"
    subst = {x: subst[x] for arg in protocol.type_args for x in arg.unsolved_vars}
    return ImplProof(member_impls), subst


# TODO Move to engine
def get_instance_func(ty: Type | TypeDef, name: str) -> CallableDef | None:
        """Looks up an instance function with a given name for a type.

        Returns `None` if the name doesn't exist or isn't a function.
        """
        type_defn: TypeDef
        match ty:
            case TypeDef() as type_defn:
                pass
            case BoundTypeVar() | ExistentialTypeVar() | SumType():
                # TODO could have a bound that gives us a function 
                # Maybe ProtocolFunctionDef / ProtocolCall ??
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

        type_defn = cast(TypeDef, ENGINE.get_checked(type_defn.id))
        if type_defn.id in DEF_STORE.impls and name in DEF_STORE.impls[type_defn.id]:
            def_id = DEF_STORE.impls[type_defn.id][name]
            defn = ENGINE.get_parsed(def_id)
            if isinstance(defn, CallableDef):
                return defn
        return None
