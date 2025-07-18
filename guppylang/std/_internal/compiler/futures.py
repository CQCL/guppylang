from collections.abc import Callable, Sequence

from hugr import ops
from hugr import tys as ht

from guppylang.error import InternalGuppyError
from guppylang.std._internal.compiler.tket2_exts import FUTURES_EXTENSION
from guppylang.tys.arg import Argument, TypeArg
from guppylang.tys.subst import Inst


def future_to_hugr(type_args: Sequence[Argument]) -> ht.Type:
    match type_args:
        case [TypeArg(ty)]:
            type_def = FUTURES_EXTENSION.get_type("Future")
            return type_def.instantiate([ht.TypeTypeArg(ty.to_hugr())])
        case _:
            raise InternalGuppyError("Invalid type args for Future type")


def future_op(op_name: str) -> Callable[[ht.FunctionType, Inst], ops.DataflowOp]:
    op_def = FUTURES_EXTENSION.get_op(op_name)

    def op(concrete: ht.FunctionType, args: Inst) -> ops.DataflowOp:
        return op_def.instantiate([arg.to_hugr() for arg in args], concrete)

    return op
