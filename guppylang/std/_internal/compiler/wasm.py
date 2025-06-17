import ast
from dataclasses import dataclass

import hugr.model
import hugr.std
from hugr import Wire, ops, val
from hugr import tys as ht
from tket2.extensions import futures, wasm

from guppylang.checker.errors.type_errors import WasmTypeConversionError
from guppylang.checker.errors.wasm import (
    FirstArgNotModule,
    NonFunctionWasmType,
    UnWasmableType,
)
from guppylang.checker.expr_checker import check_call, synthesize_call
from guppylang.definition.custom import CustomCallChecker, CustomInoutCallCompiler
from guppylang.definition.value import CallReturnWires

# from guppylang.definition.wasm import WasmModule
from guppylang.error import GuppyError, GuppyTypeError
from guppylang.nodes import GlobalCall, LocalCall
from guppylang.std._internal.compiler.prelude import build_unwrap
from guppylang.tys.arg import ConstArg, TypeArg
from guppylang.tys.builtin import (
    is_array_type,
    is_bool_type,
    is_string_type,
    is_wasm_module_type,
    string_type,
)
from guppylang.tys.const import ConstValue
from guppylang.tys.constarg import ConstStringArg
from guppylang.tys.subst import Subst
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


class WasmCallChecker(CustomCallChecker):
    type_sanitised: bool = False

    def sanitise_type(self) -> None:
        # Place to highlight in error messages
        loc = self.func.defined_at

        if isinstance(self.func.ty, FunctionType):
            match self.func.ty.inputs[0]:
                case FuncInput(ty=ty, flags=InputFlags.Inout) if is_wasm_module_type(
                    ty
                ):
                    pass
                case FuncInput(ty=ty):
                    raise GuppyError(FirstArgNotModule(loc, ty))
            for inp in self.func.ty.inputs[1:]:
                if not self.is_type_wasmable(inp.ty):
                    raise GuppyError(UnWasmableType(loc, inp.ty))
            if not self.is_type_wasmable(self.func.ty.output):
                raise GuppyError(UnWasmableType(loc, self.func.ty.output))
        else:
            raise GuppyError(NonFunctionWasmType(loc, self.func.ty))
        self.type_sanitised = True

    def is_type_wasmable(self, ty: Type) -> bool:
        match ty:
            case NumericType():
                return True
            case NoneType():
                return True
            case TupleType(element_types=tys):
                return all(self.is_type_wasmable(ty) for ty in tys)
            case FunctionType() as f:
                return self.is_type_wasmable(f.output) and all(
                    self.is_type_wasmable(inp.ty) and inp.flags != InputFlags.Inout
                    for inp in f.inputs
                )
            case OpaqueType() as ty:
                if is_string_type(ty):
                    return True
                elif is_array_type(ty):
                    return all(
                        self.is_type_wasmable(arg.ty)
                        for arg in ty.args
                        if isinstance(arg, TypeArg)
                    )
                return is_bool_type(ty)
            case _:
                return False

    def check(self, args: list[ast.expr], ty: Type) -> tuple[ast.expr, Subst]:
        if not self.is_type_wasmable(ty):
            raise GuppyTypeError(WasmTypeConversionError(self.node, ty))

        # Use default implementation from the expression checker
        args, subst, inst = check_call(self.func.ty, args, ty, self.node, self.ctx)

        return GlobalCall(
            def_id=self.func.id, args=args, type_args=inst, cached_sig=self.func.ty
        ), subst

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        if not self.type_sanitised:
            self.sanitise_type()

        # Use default implementation from the expression checker
        args, ty, inst = synthesize_call(self.func.ty, args, self.node, self.ctx)
        return GlobalCall(
            def_id=self.func.id, args=args, type_args=inst, cached_sig=self.func.ty
        ), ty


# Compiler for initialising WASM modules
class WasmModuleInitCompiler(CustomInoutCallCompiler):
    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        # Make a ConstWasmModule as a CustomConst
        assert len(args) == 1
        w = wasm()
        ctx_arg = args[0]
        # hugr-py doesn't yet export a method to load a usize directly?
        convert_op = ops.ExtOp(
            hugr.std.int.CONVERSIONS_EXTENSION.get_op("itousize"),
            ht.FunctionType([hugr.std.int.int_t(NumericType.INT_WIDTH)], [ht.USize()]),
        )
        ctx_wire = self.builder.add_op(convert_op, ctx_arg)

        get_ctx_op = w.get_op("get_context").instantiate([])
        node = self.builder.add_op(get_ctx_op, ctx_wire)
        # TODO: Unpack the option return type fro get_context
        opt_w: Wire = node[0]
        err = "Failed to spawn WASM context"
        ws: list[Wire] = list(build_unwrap(self.builder, opt_w, err))
        assert len(ws) == 1
        return CallReturnWires(regular_returns=ws, inout_returns=[])


# Compiler for initialising WASM modules
class WasmModuleDiscardCompiler(CustomInoutCallCompiler):
    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        assert len(args) == 1
        ctx = args[0]
        w = wasm()
        op = w.get_op("dispose_context").instantiate([])
        self.builder.add_op(op, ctx)
        return CallReturnWires(regular_returns=[], inout_returns=[])


# Compiler for WASM calls
# When a wasm method s called in guppy, we turn it into 2 tket2 ops:
# - the lookup: wasmmodule -> wasmfunc
# - the call: wasmcontext * wasmfunc * inputs -> wasmcontext * output
class WasmModuleCallCompiler(CustomInoutCallCompiler):
    fn_name: str

    def __init__(self, name: str) -> None:
        self.fn_name = name

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        # The arguments should be:
        # - a WASM context
        # - any args meant for the WASM function
        assert len(args) >= 1
        w = wasm()
        fu = futures()
        module_ty = w.get_type("module").instantiate([])
        ctx_ty = w.get_type("context").instantiate([])

        fn_name_arg = ConstStringArg(ConstValue(string_type(), self.fn_name)).to_hugr()
        # Function type without Inout context arg (for building)
        assert isinstance(self.node, GlobalCall)
        assert self.node.cached_sig is not None
        wasm_sig = FunctionType(
            self.node.cached_sig.inputs[1:],
            self.node.cached_sig.output,
        ).to_hugr()

        inputs_row_arg = ht.SequenceArg([ty.type_arg() for ty in wasm_sig.input])
        output_row_arg = ht.SequenceArg([ty.type_arg() for ty in wasm_sig.output])

        func_ty = w.get_type("func").instantiate([inputs_row_arg, output_row_arg])
        future_ty = fu.get_type("Future").instantiate(
            [ht.Tuple(*wasm_sig.output).type_arg()]
        )

        # Get the WASM module information from the type
        assert isinstance(self.node, GlobalCall | LocalCall)
        selfarg = self.node.cached_sig.inputs[0].ty
        assert is_wasm_module_type(selfarg)

        # Make a ConstWasmModule so we can lookup WASM functions in it
        arg_vals = [
            arg.const.value
            for arg in selfarg.args
            if isinstance(arg, ConstArg) and isinstance(arg.const, ConstValue)
        ]
        const_module = self.builder.add_const(ConstWasmModule(*arg_vals))
        wasm_module = self.builder.load(const_module)

        # Lookup the function we want
        wasm_opdef = w.get_op("lookup").instantiate(
            [fn_name_arg, inputs_row_arg, output_row_arg],
            ht.FunctionType([module_ty], [func_ty]),
        )
        wasm_func = self.builder.add_op(wasm_opdef, wasm_module)

        # Call the function
        call_op = w.get_op("call").instantiate(
            [inputs_row_arg, output_row_arg],
            ht.FunctionType([ctx_ty, func_ty, *wasm_sig.input], [ctx_ty, future_ty]),
        )

        ctx, future = self.builder.add_op(call_op, args[0], wasm_func, *args[1:])

        read_opdef = fu.get_op("Read").instantiate(
            [ht.Tuple(*wasm_sig.output).type_arg()],
            ht.FunctionType([future_ty], [ht.Tuple(*wasm_sig.output)]),
        )
        result = self.builder.add_op(read_opdef, future)
        ws: list[Wire] = list(result[:])
        node = self.builder.add_op(ops.UnpackTuple(wasm_sig.output), *ws)
        ws: list[Wire] = list(node[:])

        return CallReturnWires(regular_returns=ws, inout_returns=[ctx])


@dataclass(frozen=True)
class ConstWasmModule(val.ExtensionValue):
    """Python wrapper for the tket2 ConstWasmModule type"""

    wasm_file: str
    wasm_hash: int

    def to_value(self) -> val.Extension:
        w = wasm()
        ty = w.get_type("module").instantiate([])

        name = "tket2.wasm.ConstWasmModule"
        payload = {"name": self.wasm_file, "hash": self.wasm_hash}
        return val.Extension(name, typ=ty, val=payload, extensions=["tket2.wasm"])

    def __str__(self) -> str:
        return (
            f"ConstWasmModule(wasm_file={self.wasm_file}, wasm_hash={self.wasm_hash})"
        )

    def to_model(self) -> hugr.model.Term:
        file_tm = hugr.model.Literal(self.wasm_file)
        hash_tm = hugr.model.Literal(self.wasm_hash)

        return hugr.model.Apply("tket2.wasm.ConstWasmModule", [file_tm, hash_tm])
