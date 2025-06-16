from guppylang.decorator import guppy
from guppylang.std._internal.util import int_op
from guppylang.tys.ty import (
    FuncInput,
    FunctionType,
    InputFlags,
    NumericType,
)
from guppylang.error import GuppyTypeError

# Define custom signature for iadd operation
ty = FunctionType(
    params=[],
    inputs=[
        FuncInput(NumericType(kind=NumericType.Kind.Int), InputFlags.NoFlags),
        FuncInput(NumericType(kind=NumericType.Kind.Int), InputFlags.NoFlags),
    ],
    output=NumericType(kind=NumericType.Kind.Int),
)


# Create hugr_op using custom signature
@guppy.hugr_op(int_op("iadd"), signature=ty)
def test_op(*args) -> None: ...


def test_custom_signature_success(validate):
    @guppy
    def test_func() -> None:
        test_op(1, 1)

    validate(test_func.compile())


def test_custom_signature_fail(validate):
    @guppy
    def test_func_fail() -> None:
        test_op(1.0, 1.0)

    try:
        validate(test_func_fail.compile())
    except GuppyTypeError as e:
        assert True
