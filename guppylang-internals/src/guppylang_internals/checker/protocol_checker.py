from abc import ABC
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TypeAlias

from guppylang_internals.definition.common import DefId
from guppylang_internals.definition.protocol import CheckedProtocolDef
from guppylang_internals.engine import ENGINE
from guppylang_internals.tys.arg import Argument
from guppylang_internals.tys.protocol import ProtocolInst
from guppylang_internals.tys.subst import Inst, Subst
from guppylang_internals.tys.ty import (
    BoundTypeVar,
    FunctionType,
    Type,
    unify,
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
    #     assert self.member_impls.keys() == self.proto.members.keys()


@dataclass(frozen=True)
class AssumptionImplProof(ImplProofBase):
    ty: BoundTypeVar

    def __post_init__(self) -> None:
        super().__post_init__()
        assert self.proto in self.ty.implements


ImplProof: TypeAlias = ConcreteImplProof | AssumptionImplProof


def unify_args(
    xs: Sequence[Argument], ys: Sequence[Argument], subst: Subst
) -> Subst | None:
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
        return AssumptionImplProof(
            protocol.substitute(subst), ty.substitute(subst)
        ), subst

    subst: Subst | None = {}
    member_impls = {}
    for name, def_id in protocol_def.members.items():
        proto_sig = ENGINE.get_checked(def_id).ty
        assert isinstance(proto_sig, FunctionType)
        # Partially instantiate proto_sig with `protocol.type_args` and `ty`
        func = ENGINE.get_instance_func(ty, name)
        if not func:
            raise "Missing member implementation"
        impl_sig, impl_vars = func.ty.unquantified()
        # TODO Make this a method
        # proto_sig_params = proto_sig.params
        proto_sig = FunctionType(proto_sig.inputs, proto_sig.output, params=[])
        subst = unify(proto_sig, impl_sig, subst)
        if subst is None:
            raise "Signature Mismatch"
        if any(x not in subst for x in impl_vars):
            raise ""
        member_impls[name] = (func.id, [subst[x] for x in impl_vars])

    if any(x not in subst for arg in protocol.type_args for x in arg.unsolved_vars):
        raise "Couldn't figure out variables in protocol"
    subst = {x: subst[x] for arg in protocol.type_args for x in arg.unsolved_vars}
    return ConcreteImplProof(protocol, ty, member_impls), subst
