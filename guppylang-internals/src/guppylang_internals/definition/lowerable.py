from dataclasses import dataclass
from typing import TYPE_CHECKING

from guppylang_internals.compiler.core import (
    GlobalConstId,
)
from guppylang_internals.definition.custom import (
    CustomFunctionDef,
    RawCustomFunctionDef,
)
from guppylang_internals.span import SourceMap
from guppylang_internals.tys.ty import (
    FunctionType,
    NoneType,
)

if TYPE_CHECKING:
    from guppylang_internals.checker.core import Globals


@dataclass(frozen=True)
class RawLowerableFunctionDef(RawCustomFunctionDef):
    """A raw custom function definition provided by the user.

    Custom functions provide their own checking and compilation logic using a
    `CustomCallChecker` and a `CustomCallCompiler`.

    The raw definition stores exactly what the user has written (i.e. the AST together
    with the provided checker and compiler), without inspecting the signature.

    Args:
        id: The unique definition identifier.
        name: The name of the definition.
        defined_at: The AST node where the definition was defined.
        call_checker: The custom call checker.
        call_compiler: The custom call compiler.
        higher_order_value: Whether the function may be used as a higher-order value.
        signature: Optional User-provided signature.
    """

    def parse(self, globals: "Globals", sources: SourceMap) -> "CustomFunctionDef":
        """Parses and checks the signature of the lowerable function.

        The signature is optional if custom type checking logic is provided by the user.
        However, a signature *must* be provided to use the function as a higher-order
        value (either by annotation or as an argument). If a signature is provided as an
        argument, this will override any annotation.

        If no signature is provided, we fill in the dummy signature `() -> ()`. This
        type will never be inspected, since we rely on the provided custom checking
        code. The only information we need to access is that it's a function type and
        that there are no unsolved existential vars.
        """
        from guppylang_internals.definition.function import parse_py_func

        func_ast, _ = parse_py_func(self.python_func, sources)
        sig = self.signature or self._get_signature(func_ast, globals)
        ty = sig or FunctionType([], NoneType())
        return CustomFunctionDef(
            self.id,
            self.name,
            func_ast,
            ty,
            self.call_checker,
            self.call_compiler,
            self.higher_order_value,
            GlobalConstId.fresh(self.name),
            sig is not None,
        )
