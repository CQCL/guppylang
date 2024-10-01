from guppylang.tys.builtin import array_type_def
from guppylang.tys.param import ConstParam, TypeParam
from guppylang.tys.ty import (
    FunctionType,
    FuncInput,
    NumericType,
    OpaqueType,
    InputFlags,
)


def test_generic_function_type():
    ty_param = TypeParam(0, "T", can_be_linear=True)
    len_param = ConstParam(1, "n", NumericType(NumericType.Kind.Nat))
    array_ty = OpaqueType([ty_param.to_bound(0), len_param.to_bound(1)], array_type_def)
    ty = FunctionType(
        params=[ty_param, len_param],
        inputs=[FuncInput(array_ty, InputFlags.Inout)],
        output=ty_param.to_bound(0).ty,
    )
    assert str(ty) == "forall T, n: nat. array[T, n] -> T"
