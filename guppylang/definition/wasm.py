from typing import TYPE_CHECKING

from guppylang.ast_util import AstNode
from guppylang.checker.errors.wasm import (
    FirstArgNotModule,
    UnWasmableType,
)
from guppylang.definition.custom import CustomFunctionDef, RawCustomFunctionDef
from guppylang.error import GuppyError
from guppylang.span import SourceMap
from guppylang.tys.builtin import wasm_module_info
from guppylang.tys.ty import (
    FuncInput,
    FunctionType,
    InputFlags,
    NoneType,
    NumericType,
    TupleType,
    Type,
)

if TYPE_CHECKING:
    from guppylang.checker.core import Globals


class RawWasmFunctionDef(RawCustomFunctionDef):
    def sanitise_type(self, loc: AstNode | None, fun_ty: FunctionType) -> None:
        # Place to highlight in error messages
        match fun_ty.inputs[0]:
            case FuncInput(ty=ty, flags=InputFlags.Inout) if wasm_module_info(
                ty
            ) is not None:
                pass
            case FuncInput(ty=ty):
                raise GuppyError(FirstArgNotModule(loc, ty))
        for inp in fun_ty.inputs[1:]:
            if not self.is_type_wasmable(inp.ty):
                raise GuppyError(UnWasmableType(loc, inp.ty))
        if not self.is_type_wasmable(fun_ty.output):
            match fun_ty.output:
                case NoneType():
                    pass
                case _:
                    raise GuppyError(UnWasmableType(loc, fun_ty.output))

    def is_type_wasmable(self, ty: Type) -> bool:
        match ty:
            case NumericType():
                return True
            case TupleType(element_types=tys):
                return all(self.is_type_wasmable(ty) for ty in tys)

        return False

    def parse(self, globals: "Globals", sources: SourceMap) -> "CustomFunctionDef":
        parsed = super().parse(globals, sources)
        self.sanitise_type(parsed.defined_at, parsed.ty)
        return parsed
