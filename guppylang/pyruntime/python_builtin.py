"""Implementation of various bits of Hugr stdlib in python."""

from copy import deepcopy
from dataclasses import dataclass
from typing import cast

from hugr import ops, tys, val
from hugr.std.collections.array import ArrayVal
from hugr.std.int import IntVal
from hugr.val import Value


@dataclass
class USizeVal(val.ExtensionValue):
    v: int

    def to_value(self) -> val.Extension:
        return val.Extension(
            "ConstUSize",
            typ=tys.USize(),
            val={"value": self.v},  # or just the int without the dict?
        )

    def __str(self) -> str:
        return f"{self.v}"


def usize_to_py(v: Value) -> int:
    ev: val.Extension = (
        v if isinstance(v, val.Extension) else cast(val.ExtensionValue, v).to_value()
    )
    u = ev.val["value"]
    assert isinstance(u, int)
    return u


async def run_ext_op(op: ops.Custom, inputs: list[Value]) -> list[Value]:
    def two_ints_logwidth() -> tuple[int, int, int]:
        (a, b) = inputs
        if not isinstance(a, val.Extension):
            a = cast(val.ExtensionValue, a).to_value()
        av = a.val["value"]
        assert isinstance(av, int)

        if not isinstance(b, val.Extension):
            b = cast(val.ExtensionValue, b).to_value()
        bv = b.val["value"]
        assert isinstance(bv, int)

        lw = a.val["log_width"]
        assert isinstance(lw, int)
        assert lw == b.val["log_width"]
        return av, bv, lw

    def one_int_logwidth() -> tuple[int, int]:
        (a,) = inputs
        if not isinstance(a, val.Extension):
            a = cast(val.ExtensionValue, a).to_value()
        av = a.val["value"]
        assert isinstance(av, int)

        lw = a.val["log_width"]
        assert isinstance(lw, int)
        return av, lw

    if op.extension == "arithmetic.conversions":
        if op.op_name == "itousize":
            (a, _) = one_int_logwidth()
            return [USizeVal(a)]
    elif op.extension == "arithmetic.int":
        if op.op_name in ["ilt_u", "ilt_s"]:  # TODO how does signedness work here
            (a, b, _) = two_ints_logwidth()
            return [val.TRUE if a < b else val.FALSE]
        if op.op_name in ["igt_u", "igt_s"]:  # TODO how does signedness work here
            (a, b, _) = two_ints_logwidth()
            return [val.TRUE if a > b else val.FALSE]
        if op.op_name == "isub":
            (a, b, lw) = two_ints_logwidth()
            # TODO: wrap/underflow to appropriate width
            return [IntVal(a - b, lw)]
        if op.op_name == "imul":
            (a, b, lw) = two_ints_logwidth()
            # TODO: wrap/overflow to appropriate width
            return [IntVal(a * b, lw)]
        if op.op_name == "iadd":
            (a, b, lw) = two_ints_logwidth()
            # TODO: wrap/underflow to appropriate width
            return [IntVal(a + b, lw)]
        if op.op_name in ["idiv_s", "idiv_u"]:  # TODO how does signedness work here
            (a, b, lw) = two_ints_logwidth()
            return [IntVal(a // b, lw)]
        if op.op_name in ["imod_s", "imod_u"]:  # TODO how does signedness work here
            (a, b, lw) = two_ints_logwidth()
            return [IntVal(a % b, lw)]
        if op.op_name in ["idivmod_s", "idivmod_u"]:
            # TODO how does signedness work here
            (a, b, lw) = two_ints_logwidth()
            return [IntVal(a // b, lw), IntVal(a % b, lw)]
        if op.op_name == "ineg":
            (a, lw) = one_int_logwidth()
            return [IntVal(-a, lw)]
    elif op.extension == "collections.array":
        if op.op_name == "new_array":
            (length, elem_type) = op.args
            assert length == tys.BoundedNatArg(len(inputs))
            assert isinstance(elem_type, tys.TypeTypeArg)
            return [ArrayVal(inputs, elem_type.ty)]
        elif op.op_name == "get":
            (array, index) = inputs
            idx = usize_to_py(index)
            if isinstance(array, ArrayVal):
                return [
                    val.None_(array.ty.ty)
                    if idx >= len(array.v)
                    else val.Some(array.v[idx])
                ]
            raise RuntimeError("YES THIS HAPPENS - non-ArrayVal array")
            assert isinstance(array, val.Extension)
            ar = array.val["values"]
            ty = array.val["typ"].deserialize()
            return [
                val.None_(ty) if idx >= len(ar) else val.Some(ar[idx].deserialize())
            ]
        elif op.op_name in ["pop_left", "pop_right"]:
            (array,) = inputs
            assert isinstance(array, ArrayVal)
            if len(array.v) == 0:
                return [val.None_(array.ty.ty)]
            elem, rest = (
                (array.v[0], array.v[1:])
                if op.op_name == "pop_left"
                else (array.v[-1], array.v[:-1])
            )
            return [val.Some(elem, ArrayVal(rest, array.ty.ty))]
        elif op.op_name == "repeat":
            from .python_runtime import _single, do_eval

            (func,) = inputs
            (length, elem_ty, _exts) = op.args
            assert isinstance(length, tys.BoundedNatArg)
            assert isinstance(elem_ty, tys.TypeTypeArg)
            return [
                ArrayVal(
                    [_single(await do_eval(func)) for _ in range(length.n)], elem_ty.ty
                )
            ]
        elif op.op_name == "set":
            (array, index, new_val) = inputs
            idx = usize_to_py(index)
            if isinstance(array, ArrayVal):
                other_tys = [array.ty.ty, array.ty]
                if idx >= len(array.v):
                    return [val.Left([new_val, array], other_tys)]
                else:
                    array = deepcopy(array)
                    old_val = array.v[idx]
                    array.v[idx] = new_val
                    return [val.Right(other_tys, [old_val, array])]
            raise RuntimeError("YES THIS HAPPENS - non-ArrayVal array")
    elif op.extension == "logic":
        if op.op_name == "Not":
            (x,) = inputs
            return [bool_to_val(not val_to_bool(x))]
        if op.op_name == "Eq":  # Yeah, presumably case sensitive, so why not 'eq'
            (x, y) = inputs
            return [bool_to_val(val_to_bool(x) == val_to_bool(y))]
    elif op.extension == "prelude" and op.op_name == "load_nat":
        (v,) = op.args
        assert isinstance(v, tys.BoundedNatArg)
        return [USizeVal(v.n)]
    raise RuntimeError(f"Unknown op {op}")


def val_to_bool(v: Value) -> bool:
    assert v in [val.TRUE, val.FALSE]
    return v == val.TRUE


def bool_to_val(b: bool) -> Value:
    return val.TRUE if b else val.FALSE
