import functools
import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from guppy.ast_util import AstNode, has_empty_body
from guppy.checker.core import PyScope
from guppy.custom import (
    CustomCallChecker,
    CustomCallCompiler,
    CustomFunction,
    DefaultCallChecker,
    DefaultCallCompiler,
    OpCompiler,
)
from guppy.error import GuppyError, pretty_errors
from guppy.gtypes import GuppyType
from guppy.hugr import ops, tys
from guppy.hugr.hugr import Hugr
from guppy.module import GuppyModule, PyFunc, parse_py_func

FuncDecorator = Callable[[PyFunc], PyFunc]
CustomFuncDecorator = Callable[[PyFunc], CustomFunction]
ClassDecorator = Callable[[type], type]


class _Guppy:
    """Class for the `@guppy` decorator."""

    # The current module
    _module: GuppyModule | None

    def __init__(self) -> None:
        self._module = None

    def set_module(self, module: GuppyModule) -> None:
        self._module = module

    @pretty_errors
    def __call__(self, arg: PyFunc | GuppyModule) -> Hugr | None | FuncDecorator:
        """Decorator to annotate Python functions as Guppy code.

        Optionally, the `GuppyModule` in which the function should be placed can be
        passed to the decorator.
        """
        if isinstance(arg, GuppyModule):

            def dec(f: Callable[..., Any]) -> Callable[..., Any]:
                assert isinstance(arg, GuppyModule)
                arg.register_func_def(f, get_python_scope())

                @functools.wraps(f)
                def dummy(*args: Any, **kwargs: Any) -> Any:
                    raise GuppyError(
                        "Guppy functions can only be called in a Guppy context"
                    )

                return dummy

            return dec
        else:
            module = self._module or GuppyModule("module")
            module.register_func_def(arg, get_python_scope())
            return module.compile()

    @pretty_errors
    def extend_type(self, module: GuppyModule, ty: type[GuppyType]) -> ClassDecorator:
        """Decorator to add new instance functions to a type."""
        module._instance_func_buffer = {}

        def dec(c: type) -> type:
            module._register_buffered_instance_funcs(ty, get_python_scope())
            return c

        return dec

    @pretty_errors
    def type(
        self,
        module: GuppyModule,
        hugr_ty: tys.SimpleType,
        name: str = "",
        linear: bool = False,
    ) -> ClassDecorator:
        """Decorator to annotate a class definitions as Guppy types.

        Requires the static Hugr translation of the type. Additionally, the type can be
        marked as linear. All `@guppy` annotated functions on the class are turned into
        instance functions.
        """
        module._instance_func_buffer = {}

        def dec(c: type) -> type:
            _name = name or c.__name__

            @dataclass(frozen=True)
            class NewType(GuppyType):
                name = _name

                @staticmethod
                def build(*args: GuppyType, node: AstNode | None = None) -> "GuppyType":
                    # At the moment, custom types don't support type arguments.
                    if len(args) > 0:
                        raise GuppyError(
                            f"Type `{_name}` does not accept type parameters.", node
                        )
                    return NewType()

                @property
                def linear(self) -> bool:
                    return linear

                def to_hugr(self) -> tys.SimpleType:
                    return hugr_ty

                def __str__(self) -> str:
                    return _name

            NewType.__name__ = name
            NewType.__qualname__ = _name
            module.register_type(_name, NewType)
            module._register_buffered_instance_funcs(NewType, get_python_scope())
            setattr(c, "_guppy_type", NewType)
            return c

        return dec

    @pretty_errors
    def custom(
        self,
        module: GuppyModule,
        compiler: CustomCallCompiler | None = None,
        checker: CustomCallChecker | None = None,
        higher_order_value: bool = True,
        name: str = "",
    ) -> CustomFuncDecorator:
        """Decorator to add custom typing or compilation behaviour to function decls.

        Optionally, usage of the function as a higher-order value can be disabled. In
        that case, the function signature can be omitted if a custom call compiler is
        provided.
        """

        def dec(f: PyFunc) -> CustomFunction:
            func_ast = parse_py_func(f)
            if not has_empty_body(func_ast):
                raise GuppyError(
                    "Body of custom function declaration must be empty",
                    func_ast.body[0],
                )
            call_checker = checker or DefaultCallChecker()
            func = CustomFunction(
                name or func_ast.name,
                func_ast,
                compiler or DefaultCallCompiler(),
                call_checker,
                higher_order_value,
            )
            call_checker.func = func
            module.register_custom_func(func)
            return func

        return dec

    def hugr_op(
        self,
        module: GuppyModule,
        op: ops.OpType,
        checker: CustomCallChecker | None = None,
        higher_order_value: bool = True,
        name: str = "",
    ) -> CustomFuncDecorator:
        """Decorator to annotate function declarations as HUGR ops."""
        return self.custom(module, OpCompiler(op), checker, higher_order_value, name)

    def declare(self, module: GuppyModule) -> FuncDecorator:
        """Decorator to declare functions"""

        def dec(f: Callable[..., Any]) -> Callable[..., Any]:
            module.register_func_decl(f)

            @functools.wraps(f)
            def dummy(*args: Any, **kwargs: Any) -> Any:
                raise GuppyError(
                    "Guppy functions can only be called in a Guppy context"
                )

            return dummy

        return dec


guppy = _Guppy()


def get_python_scope() -> PyScope:
    """Looks up all available Python variables from the call-site.

    Walks up the call stack until we have left the `guppy` module.
    """
    # Note that this approach will yield unintended results if the user doesn't invoke
    # the decorator directly. For example:
    #
    #       def my_dec(f):
    #           some_local = ...
    #           return guppy(f)
    #
    #       @my_dec
    #       def guppy_func(x: int) -> int:
    #           ....
    #
    # Here, we would reach the scope of `my_dec` and `some_local` would be available
    # in the Guppy code.
    # TODO: Is there a better way to obtain the variables in scope? Note that we
    #  could do `inspect.getclosurevars(f)` but it will fail if `f` has recursive
    #  calls. A custom solution based on `f.__code__.co_freevars` and
    #  `f.__closure__` would only work for CPython.
    frame = inspect.currentframe()
    if frame is None:
        return {}
    while frame.f_back is not None and frame.f_globals["__name__"].startswith("guppy."):
        frame = frame.f_back
    py_scope = frame.f_globals | frame.f_locals
    # Explicitly delete frame to avoid reference cycle.
    # See https://docs.python.org/3/library/inspect.html#the-interpreter-stack
    del frame
    return py_scope
