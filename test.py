from guppylang import guppy
from guppylang.checker.protocol_checker import check_protocol, ConcreteImplProof, AssumptionImplProof
from guppylang.definition.common import DefId
from guppylang.definition.protocol import CheckedProtocolDef
from guppylang.tys.ty import FunctionType, NumericType, FuncInput, InputFlags, ExistentialTypeVar, BoundTypeVar
from guppylang.tys.var import ExistentialVar
from guppylang.tys.param import TypeParam
from guppylang.tys.protocol import ProtocolInst
from guppylang.engine import ENGINE
from guppylang.std.builtins import nat

T = ExistentialTypeVar.fresh("T", True, True)

param = TypeParam(0, "Input", True, True, [])

members = {"foo": FunctionType(inputs=[FuncInput(T, flags=InputFlags.NoFlags), FuncInput(NumericType(NumericType.Kind.Nat), flags=InputFlags.NoFlags)],
                               output=NumericType(NumericType.Kind.Float),
                               params=[param])
           }
#members = {"foo": FunctionType(inputs=[FuncInput(T, flags=InputFlags.NoFlags), FuncInput(param.to_bound().ty, flags=InputFlags.NoFlags)],
#                               output=NumericType(NumericType.Kind.Float),
#                               params=[param])
#           }

proto_def = CheckedProtocolDef(DefId.fresh(), "MyProto", None, [], members)
proto = ProtocolInst([], proto_def)

@guppy.struct
class MyClass:
    @guppy
    def foo[T](self: "MyClass", x: T) -> float:
        return "42.0"

ENGINE.reset()
class_def = ENGINE.get_checked(MyClass.id)

# ty_def = class_def.check_instantiate([])
ty_def = BoundTypeVar(0, "MyType", [proto], True, True)

print(check_protocol(ty_def, proto))
