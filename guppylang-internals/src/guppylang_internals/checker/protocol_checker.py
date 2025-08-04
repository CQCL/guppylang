
from dataclasses import replace
from types import NoneType
from typing import assert_never, cast
from guppylang_internals.definition.protocol import CheckedProtocolDef
from guppylang_internals.definition.ty import TypeDef
from guppylang_internals.definition.value import CallableDef
from guppylang_internals.engine import DEF_STORE, ENGINE
from guppylang_internals.tys.protocol import ProtocolInst
from guppylang_internals.tys.subst import Subst
from guppylang_internals.tys.ty import BoundTypeVar, ExistentialTypeVar, FunctionType, NumericType, OpaqueType, StructType, SumType, TupleType, Type, unify
from guppylang_internals.tys.builtin import (
    callable_type_def,
    float_type_def,
    int_type_def,
    nat_type_def,
    none_type_def,
    tuple_type_def,
)


def check_protocol(ty: Type, protocol: ProtocolInst) -> Subst:
    # Invariant: ty and protocol might have unsolved variables
    protocol_def = ENGINE.get_checked(protocol.definition)
    assert isinstance(protocol_def, CheckedProtocolDef)
    subst: Subst | None = {}
    for name, proto_sig in protocol_def.members.items():
        func = get_instance_func(ty, name)
        if not func:
            raise "Missing member implementation"
        impl_sig, impl_vars = func.ty.unquantified()
        # TODO Make this a method
        proto_sig_params = proto_sig.params
        proto_sig = replace(proto_sig, params=[])
        subst = unify(proto_sig, impl_sig, subst)
        if subst is None:
            raise "Signature Mismatch"
        if not all(x in subst.keys() for x in impl_vars):
            raise ""
    # TODO: Check all proto parameters in subst
        


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
