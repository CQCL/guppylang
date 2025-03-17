"""Compilers building array functions on top of hugr standard operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, TypeVar

from hugr import Wire, ops
from hugr import tys as ht
from hugr.std.collections.array import EXTENSION

from guppylang.compiler.core import (
    GlobalConstId,
)
from guppylang.definition.custom import CustomCallCompiler
from guppylang.definition.value import CallReturnWires
from guppylang.error import InternalGuppyError
from guppylang.std._internal.compiler.arithmetic import convert_itousize
from guppylang.std._internal.compiler.prelude import (
    build_expect_none,
    build_unwrap,
    build_unwrap_left,
    build_unwrap_right,
)
from guppylang.tys.arg import ConstArg, TypeArg
from guppylang.tys.builtin import int_type

if TYPE_CHECKING:
    from hugr.build import function as hf
    from hugr.build.dfg import DfBase


# ------------------------------------------------------
# --------------- std.array operations -----------------
# ------------------------------------------------------


def _instantiate_array_op(
    name: str,
    elem_ty: ht.Type,
    length: ht.TypeArg,
    inp: list[ht.Type],
    out: list[ht.Type],
) -> ops.ExtOp:
    return EXTENSION.get_op(name).instantiate(
        [length, ht.TypeTypeArg(elem_ty)], ht.FunctionType(inp, out)
    )


def array_type(elem_ty: ht.Type, length: ht.TypeArg) -> ht.ExtType:
    """Returns the hugr type of a fixed length array."""
    elem_arg = ht.TypeTypeArg(elem_ty)
    return EXTENSION.types["array"].instantiate([length, elem_arg])


def array_new(elem_ty: ht.Type, length: int) -> ops.ExtOp:
    """Returns an operation that creates a new fixed length array."""
    length_arg = ht.BoundedNatArg(length)
    arr_ty = array_type(elem_ty, length_arg)
    return _instantiate_array_op(
        "new_array", elem_ty, length_arg, [elem_ty] * length, [arr_ty]
    )


def array_get(elem_ty: ht.Type, length: ht.TypeArg) -> ops.ExtOp:
    """Returns an array `get` operation."""
    assert elem_ty.type_bound() == ht.TypeBound.Copyable
    arr_ty = array_type(elem_ty, length)
    return _instantiate_array_op(
        "get", elem_ty, length, [arr_ty, ht.USize()], [ht.Option(elem_ty)]
    )


def array_set(elem_ty: ht.Type, length: ht.TypeArg) -> ops.ExtOp:
    """Returns an array `set` operation."""
    arr_ty = array_type(elem_ty, length)
    return _instantiate_array_op(
        "set",
        elem_ty,
        length,
        [arr_ty, ht.USize(), elem_ty],
        [ht.Either([elem_ty, arr_ty], [elem_ty, arr_ty])],
    )


def array_pop(elem_ty: ht.Type, length: int, from_left: bool) -> ops.ExtOp:
    """Returns an operation that pops an element from the left of an array."""
    assert length > 0
    length_arg = ht.BoundedNatArg(length)
    arr_ty = array_type(elem_ty, length_arg)
    popped_arr_ty = array_type(elem_ty, ht.BoundedNatArg(length - 1))
    op = "pop_left" if from_left else "pop_right"
    return _instantiate_array_op(
        op, elem_ty, length_arg, [arr_ty], [ht.Option(elem_ty, popped_arr_ty)]
    )


def array_discard_empty(elem_ty: ht.Type) -> ops.ExtOp:
    """Returns an operation that discards an array of length zero."""
    arr_ty = array_type(elem_ty, ht.BoundedNatArg(0))
    return EXTENSION.get_op("discard_empty").instantiate(
        [ht.TypeTypeArg(elem_ty)], ht.FunctionType([arr_ty], [])
    )


def array_scan(
    elem_ty: ht.Type,
    length: ht.TypeArg,
    new_elem_ty: ht.Type,
    accumulators: list[ht.Type],
) -> ops.ExtOp:
    """Returns an operation that maps and folds a function across an array."""
    ty_args = [
        length,
        ht.TypeTypeArg(elem_ty),
        ht.TypeTypeArg(new_elem_ty),
        ht.SequenceArg([ht.TypeTypeArg(acc) for acc in accumulators]),
        ht.ExtensionsArg([]),
    ]
    ins = [
        array_type(elem_ty, length),
        ht.FunctionType([elem_ty, *accumulators], [new_elem_ty, *accumulators]),
        *accumulators,
    ]
    outs = [array_type(new_elem_ty, length), *accumulators]
    return EXTENSION.get_op("scan").instantiate(ty_args, ht.FunctionType(ins, outs))


def array_map(elem_ty: ht.Type, length: ht.TypeArg, new_elem_ty: ht.Type) -> ops.ExtOp:
    """Returns an operation that maps a function across an array."""
    return array_scan(elem_ty, length, new_elem_ty, accumulators=[])


def array_repeat(elem_ty: ht.Type, length: ht.TypeArg) -> ops.ExtOp:
    """Returns an array `repeat` operation."""
    return EXTENSION.get_op("repeat").instantiate(
        [length, ht.TypeTypeArg(elem_ty), ht.ExtensionsArg([])],
        ht.FunctionType(
            [ht.FunctionType([], [elem_ty])], [array_type(elem_ty, length)]
        ),
    )


# ------------------------------------------------------
# --------- Custom compilers for non-native ops --------
# ------------------------------------------------------


P = TypeVar("P", bound=ops.DfParentOp)


def unpack_array(builder: DfBase[P], array: Wire) -> list[Wire]:
    """ """
    # TODO: This should be an op
    array_ty = builder.hugr.port_type(array.out_port())
    assert isinstance(array_ty, ht.ExtType)
    err = "Internal error: array unpacking failed"
    match array_ty.args:
        case [ht.BoundedNatArg(length), ht.TypeTypeArg(elem_ty)]:
            elems: list[Wire] = []
            for i in range(length):
                res = builder.add_op(
                    array_pop(elem_ty, length - i, from_left=True), array
                )
                elem, array = build_unwrap(builder, res, err)
                elems.append(elem)
            builder.add_op(array_discard_empty(elem_ty), array)
            return elems
        case _:
            raise InternalGuppyError("Invalid array type args")


class ArrayCompiler(CustomCallCompiler):
    """Base class for custom array op compilers."""

    @property
    def elem_ty(self) -> ht.Type:
        """The element type for the array op that is being compiled."""
        match self.type_args:
            case [TypeArg(ty=elem_ty), _]:
                return elem_ty.to_hugr()
            case _:
                raise InternalGuppyError("Invalid array type args")

    @property
    def length(self) -> ht.TypeArg:
        """The length for the array op that is being compiled."""
        match self.type_args:
            case [_, ConstArg(const)]:  # Const includes both literals and variables
                return const.to_arg().to_hugr()
            case _:
                raise InternalGuppyError("Invalid array type args")


class NewArrayCompiler(ArrayCompiler):
    """Compiler for the `array.__new__` function."""

    def build_classical_array(self, elems: list[Wire]) -> Wire:
        """Lowers a call to `array.__new__` for classical arrays."""
        # See https://github.com/CQCL/guppylang/issues/629
        return self.build_linear_array(elems)

    def build_linear_array(self, elems: list[Wire]) -> Wire:
        """Lowers a call to `array.__new__` for linear arrays."""
        elem_opts = [
            self.builder.add_op(ops.Some(self.elem_ty), elem) for elem in elems
        ]
        return self.builder.add_op(
            array_new(ht.Option(self.elem_ty), len(elems)), *elem_opts
        )

    def compile(self, args: list[Wire]) -> list[Wire]:
        if self.elem_ty.type_bound() == ht.TypeBound.Any:
            return [self.build_linear_array(args)]
        else:
            return [self.build_classical_array(args)]


ARRAY_GETITEM_CLASSICAL: Final[GlobalConstId] = GlobalConstId.fresh(
    "array.__getitem__.classical"
)
ARRAY_GETITEM_LINEAR: Final[GlobalConstId] = GlobalConstId.fresh(
    "array.__getitem__.linear"
)
ARRAY_SETITEM_CLASSICAL: Final[GlobalConstId] = GlobalConstId.fresh(
    "array.__setitem__.classical"
)
ARRAY_SETITEM_LINEAR: Final[GlobalConstId] = GlobalConstId.fresh(
    "array.__setitem__.linear"
)
ARRAY_ITER_ASSERT_ALL_USED_HELPER: Final[GlobalConstId] = GlobalConstId.fresh(
    "ArrayIter._assert_all_used.helper"
)


class ArrayGetitemCompiler(ArrayCompiler):
    """Compiler for the `array.__getitem__` function."""

    def _getitem_ty(self, bound: ht.TypeBound) -> ht.PolyFuncType:
        """Constructs a polymorphic function type for `__getitem__`"""
        # a(Option(T), N), int -> T, a(Option(T), N)
        # Array element type parameter
        elem_ty_param = ht.TypeTypeParam(bound)
        # Array length parameter
        length_param = ht.BoundedNatParam()
        return ht.PolyFuncType(
            params=[elem_ty_param, length_param],
            body=ht.FunctionType(
                input=[
                    array_type(
                        ht.Option(ht.Variable(0, bound)),
                        ht.VariableArg(1, length_param),
                    ),
                    int_type().to_hugr(),
                ],
                output=[
                    ht.Variable(0, bound),
                    array_type(
                        ht.Option(ht.Variable(0, bound)),
                        ht.VariableArg(1, length_param),
                    ),
                ],
            ),
        )

    def _build_classical_getitem(self, func: hf.Function) -> None:
        """Constructs a generic function for `__getitem__` for classical arrays."""
        elem_ty = ht.Variable(0, ht.TypeBound.Copyable)
        length = ht.VariableArg(1, ht.BoundedNatParam())

        # See https://github.com/CQCL/guppylang/issues/629
        elem_opt_ty = ht.Option(elem_ty)
        idx = func.add_op(convert_itousize(), func.inputs()[1])
        result = func.add_op(
            array_get(elem_opt_ty, length),
            func.inputs()[0],
            idx,
        )
        elem_opt = build_unwrap(func, result, "Array index out of bounds")
        elem = build_unwrap(func, elem_opt, "array.__getitem__: Internal error")

        # Return input array unmodified for consistency with linear implementation.
        func.set_outputs(elem, func.inputs()[0])

    def _build_linear_getitem(self, func: hf.Function) -> None:
        """Constructs function to call `array.__getitem__` for linear arrays."""
        elem_ty = ht.Variable(0, ht.TypeBound.Any)
        length = ht.VariableArg(1, ht.BoundedNatParam())

        elem_opt_ty = ht.Option(elem_ty)
        none = func.add_op(ops.Tag(0, elem_opt_ty))
        idx = func.add_op(convert_itousize(), func.inputs()[1])
        result = func.add_op(
            array_set(elem_opt_ty, length),
            func.inputs()[0],
            idx,
            none,
        )
        elem_opt, array = build_unwrap_right(func, result, "Array index out of bounds")
        elem = build_unwrap(
            func, elem_opt, "Linear array element has already been used"
        )

        func.set_outputs(elem, array)

    def _build_call_getitem(
        self,
        func: hf.Function,
        array: Wire,
        idx: Wire,
    ) -> CallReturnWires:
        """Inserts a call to `array.__getitem__`."""
        concrete_func_ty = ht.FunctionType(
            input=[
                array_type(ht.Option(self.elem_ty), self.length),
                int_type().to_hugr(),
            ],
            output=[self.elem_ty, array_type(ht.Option(self.elem_ty), self.length)],
        )
        type_args = [ht.TypeTypeArg(self.elem_ty), self.length]
        func_call = self.builder.call(
            func.parent_node,
            array,
            idx,
            instantiation=concrete_func_ty,
            type_args=type_args,
        )
        outputs = list(func_call.outputs())
        return CallReturnWires(
            regular_returns=[outputs[0]],
            inout_returns=[outputs[1]],
        )

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        [array, idx] = args
        if self.elem_ty.type_bound() == ht.TypeBound.Any:
            func_ty = self._getitem_ty(ht.TypeBound.Any)
            func, already_exists = self.ctx.declare_global_func(
                ARRAY_GETITEM_LINEAR, func_ty
            )
            if not already_exists:
                self._build_linear_getitem(func)
        else:
            func_ty = self._getitem_ty(ht.TypeBound.Copyable)
            func, already_exists = self.ctx.declare_global_func(
                ARRAY_GETITEM_CLASSICAL, func_ty
            )
            if not already_exists:
                self._build_classical_getitem(func)
        return self._build_call_getitem(
            func=func,
            array=array,
            idx=idx,
        )

    def compile(self, args: list[Wire]) -> list[Wire]:
        raise InternalGuppyError("Call compile_with_inouts instead")


class ArraySetitemCompiler(ArrayCompiler):
    """Compiler for the `array.__setitem__` function."""

    def _setitem_ty(self, bound: ht.TypeBound) -> ht.PolyFuncType:
        """Constructs a polymorphic function type for `__setitem__`"""
        # a(Option(T), N), int, T -> a(Option(T), N)
        elem_ty_param = ht.TypeTypeParam(bound)
        length_param = ht.BoundedNatParam()
        return ht.PolyFuncType(
            params=[elem_ty_param, length_param],
            body=ht.FunctionType(
                input=[
                    array_type(
                        ht.Option(ht.Variable(0, bound)),
                        ht.VariableArg(1, length_param),
                    ),
                    int_type().to_hugr(),
                    ht.Variable(0, bound),
                ],
                output=[
                    array_type(
                        ht.Option(ht.Variable(0, bound)),
                        ht.VariableArg(1, length_param),
                    ),
                ],
            ),
        )

    def _build_classical_setitem(self, func: hf.Function) -> None:
        """Constructs a generic function for `__setitem__` for classical arrays."""
        elem_ty = ht.Variable(0, ht.TypeBound.Copyable)
        length = ht.VariableArg(1, ht.BoundedNatParam())

        elem_opt_ty = ht.Option(elem_ty)
        idx = func.add_op(convert_itousize(), func.inputs()[1])
        elem_opt = func.add_op(ops.Some(elem_ty), func.inputs()[2])
        result = func.add_op(
            array_set(elem_opt_ty, length),
            func.inputs()[0],
            idx,
            elem_opt,
        )
        _, array = build_unwrap_right(func, result, "Array index out of bounds")

        func.set_outputs(array)

    def _build_linear_setitem(self, func: hf.Function) -> None:
        """Constructs function to call `array.__setitem__` for linear arrays."""
        elem_ty = ht.Variable(0, ht.TypeBound.Any)
        length = ht.VariableArg(1, ht.BoundedNatParam())

        elem_opt_ty = ht.Option(elem_ty)
        elem = func.add_op(ops.Some(elem_ty), func.inputs()[2])
        idx = func.add_op(convert_itousize(), func.inputs()[1])
        result = func.add_op(
            array_set(elem_opt_ty, length),
            func.inputs()[0],
            idx,
            elem,
        )
        old_elem_opt, array = build_unwrap_right(
            func, result, "Array index out of bounds"
        )
        build_unwrap_left(func, old_elem_opt, "Linear array element has not been used")

        func.set_outputs(array)

    def _build_call_setitem(
        self,
        func: hf.Function,
        array: Wire,
        idx: Wire,
        elem: Wire,
    ) -> CallReturnWires:
        """Inserts a call to `array.__setitem__`."""
        concrete_func_ty = ht.FunctionType(
            input=[
                array_type(ht.Option(self.elem_ty), self.length),
                int_type().to_hugr(),
                self.elem_ty,
            ],
            output=[array_type(ht.Option(self.elem_ty), self.length)],
        )
        type_args = [ht.TypeTypeArg(self.elem_ty), self.length]
        func_call = self.builder.call(
            func.parent_node,
            array,
            idx,
            elem,
            instantiation=concrete_func_ty,
            type_args=type_args,
        )
        return CallReturnWires(
            regular_returns=[],
            inout_returns=list(func_call.outputs()),
        )

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        [array, idx, elem] = args
        if self.elem_ty.type_bound() == ht.TypeBound.Any:
            func_ty = self._setitem_ty(ht.TypeBound.Any)
            func, already_exists = self.ctx.declare_global_func(
                ARRAY_SETITEM_LINEAR, func_ty
            )
            if not already_exists:
                self._build_linear_setitem(func)
        else:
            func_ty = self._setitem_ty(ht.TypeBound.Copyable)
            func, already_exists = self.ctx.declare_global_func(
                ARRAY_SETITEM_CLASSICAL, func_ty
            )
            if not already_exists:
                self._build_classical_setitem(func)
        return self._build_call_setitem(func=func, array=array, idx=idx, elem=elem)

    def compile(self, args: list[Wire]) -> list[Wire]:
        raise InternalGuppyError("Call compile_with_inouts instead")


class ArrayIterAsertAllUsedCompiler(ArrayCompiler):
    """Compiler for the `ArrayIter._assert_all_used` method."""

    def compile(self, args: list[Wire]) -> list[Wire]:
        # For linear array iterators, map the array of optional elements to an
        # `array[None, n]` that we can discard.
        if self.elem_ty.type_bound() == ht.TypeBound.Any:
            elem_opt_ty = ht.Option(self.elem_ty)
            unit_ty = ht.UnitSum(1)
            # Instantiate `unwrap_none` function
            func = self.builder.load_function(
                self.define_unwrap_none_helper(),
                type_args=[ht.TypeTypeArg(self.elem_ty)],
                instantiation=ht.FunctionType([elem_opt_ty], [unit_ty]),
            )
            # Map it over the array so that the resulting array is no longer linear and
            # can be discarded
            [array_iter] = args
            array, _ = self.builder.add_op(ops.UnpackTuple(), array_iter)
            self.builder.add_op(
                array_map(elem_opt_ty, self.length, unit_ty), array, func
            )
        return []

    def define_unwrap_none_helper(self) -> hf.Function:
        """Define an `unwrap_none` function that checks that the passed element is
        indeed `None`."""
        opt_ty = ht.Option(ht.Variable(0, ht.TypeBound.Any))
        unit_ty = ht.UnitSum(1)
        func_ty = ht.PolyFuncType(
            params=[ht.TypeTypeParam(ht.TypeBound.Any)],
            body=ht.FunctionType([opt_ty], [unit_ty]),
        )
        func, already_defined = self.ctx.declare_global_func(
            ARRAY_ITER_ASSERT_ALL_USED_HELPER, func_ty
        )
        if not already_defined:
            err_msg = "ArrayIter._assert_all_used: array element has not been used"
            build_expect_none(func, func.inputs()[0], err_msg)
            func.set_outputs(func.add_op(ops.MakeTuple()))
        return func
