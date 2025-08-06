from typing import TYPE_CHECKING

from guppylang_internals.ast_util import AstNode
from guppylang_internals.checker.errors.gpu import (
    FirstArgNotModule,
    UnconvertableType,
)
from guppylang_internals.definition.custom import CustomFunctionDef, RawCustomFunctionDef
from guppylang_internals.error import GuppyError
from guppylang_internals.span import SourceMap
from guppylang_internals.tys.builtin import gpu_module_info
from guppylang_internals.tys.ty import (
    FuncInput,
    FunctionType,
    InputFlags,
    NoneType,
    NumericType,
    Type,
)

if TYPE_CHECKING:
    from guppylang_internals.checker.core import Globals


class RawGpuFunctionDef(RawCustomFunctionDef):
    def sanitise_type(self, loc: AstNode | None, fun_ty: FunctionType) -> None:
        # Place to highlight in error messages
        match fun_ty.inputs[0]:
            case FuncInput(ty=ty, flags=InputFlags.Inout) if gpu_module_info(
                ty
            ) is not None:
                pass
            case FuncInput(ty=ty):
                raise GuppyError(FirstArgNotModule(loc, ty))
        for inp in fun_ty.inputs[1:]:
            if not self.is_valid_gpu_type(inp.ty):
                raise GuppyError(UnconvertableType(loc, inp.ty))
        if not self.is_valid_gpu_type(fun_ty.output):
            match fun_ty.output:
                case NoneType():
                    pass
                case _:
                    raise GuppyError(UnconvertableType(loc, fun_ty.output))

    # TODO: What is a valid GPU type? Surely arrays?
    def is_valid_gpu_type(self, ty: Type) -> bool:
        match ty:
            case NumericType():
                return True

        return False

    def parse(self, globals: "Globals", sources: SourceMap) -> "CustomFunctionDef":
        parsed = super().parse(globals, sources)
        self.sanitise_type(parsed.defined_at, parsed.ty)
        return parsed
