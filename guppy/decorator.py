import functools
import inspect
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, TypeVar

from guppy.ast_util import AstNode, has_empty_body
from guppy.custom import (
    CustomCallChecker,
    CustomCallCompiler,
    CustomFunction,
    DefaultCallChecker,
    DefaultCallCompiler,
    OpCompiler,
)
from guppy.error import GuppyError, pretty_errors
from guppy.gtypes import GuppyType, TypeTransformer
from guppy.hugr import ops, tys
from guppy.hugr.hugr import Hugr
from guppy.module import GuppyModule, PyFunc, parse_py_func

FuncDecorator = Callable[[PyFunc], PyFunc | Hugr]
CustomFuncDecorator = Callable[[PyFunc], CustomFunction]
ClassDecorator = Callable[[type], type]


@dataclass
class CallerIdentifier:
    """Identifier for the interpreter frame that called the decorator."""

    filename: Path
    function: str

    @property
    def name(self) -> str:
        """Returns a user-friendly name for the caller.

        If the called is not a function, uses the file name.
        """
        if self.function == "<module>":
            return self.filename.name
        return self.function

    def __hash__(self) -> int:
        return hash((self.filename, self.function))


class _Guppy:
    """Class for the `@guppy` decorator."""

    # The currently-alive modules, associated with an element in the call stack.
    _modules: dict[CallerIdentifier, GuppyModule]

    def __init__(self) -> None:
        self._modules = {}

    @pretty_errors
    def __call__(
        self, arg: PyFunc | GuppyModule | None = None, *, compile: bool = False
    ) -> Hugr | None | FuncDecorator:
        """Decorator to annotate Python functions as Guppy code.

        Optionally, the `GuppyModule` in which the function should be placed can
        be passed to the decorator.

        If `compile` is set to `True` and no `GuppyModule` is passed, the
        function is compiled immediately as an standalone module and the Hugr is
        returned.
        """
        if arg is not None and not isinstance(arg, GuppyModule):
            # Decorator used without any arguments.
            f = arg
            decorator: FuncDecorator = self.__call__(None)  # type: ignore[assignment]
            return decorator(f)

        def make_dummy(wraps: PyFunc) -> Callable[..., Any]:
            @functools.wraps(wraps)
            def dummy(*args: Any, **kwargs: Any) -> Any:
                raise GuppyError(
                    "Guppy functions can only be called in a Guppy context"
                )

            return dummy

        if arg is None and compile:
            # No module passed, and compile option is set.
            def dec(f: Callable[..., Any]) -> Callable[..., Any] | Hugr:
                module = GuppyModule("module")
                module.register_func_def(f)
                compiled = module.compile()
                assert compiled is not None
                return compiled

            return dec

        if arg is None and not compile:
            # No module specified, and `compile` option is not set.
            # We use a module associate with the caller of the decorator.
            def dec(f: Callable[..., Any]) -> Callable[..., Any] | Hugr:
                caller = self._get_python_caller()
                if caller not in self._modules:
                    self._modules[caller] = GuppyModule(caller.name)
                module = self._modules[caller]
                module.register_func_def(f)
                return make_dummy(f)

            return dec

        if isinstance(arg, GuppyModule):
            # Module passed. Ignore `compile` option.

            def dec(f: Callable[..., Any]) -> Callable[..., Any] | Hugr:
                arg.register_func_def(f)
                return make_dummy(f)

            return dec

        raise ValueError(f"Invalid arguments to `@guppy` decorator: {arg}")

    def _get_python_caller(self) -> CallerIdentifier:
        """Returns an identifier for the interpreter frame that called the decorator."""
        for s in inspect.stack():
            # Note the hacky check for the pretty errors wrapper,
            # since @pretty_errors wraps the __call__ method.
            if s.filename != __file__ and s.function != "pretty_errors_wrapped":
                return CallerIdentifier(Path(s.filename), s.function)
        raise GuppyError("Could not find caller of `@guppy` decorator")

    @pretty_errors
    def extend_type(self, module: GuppyModule, ty: type[GuppyType]) -> ClassDecorator:
        """Decorator to add new instance functions to a type."""
        module._instance_func_buffer = {}

        def dec(c: type) -> type:
            module._register_buffered_instance_funcs(ty)
            return c

        return dec

    @pretty_errors
    def type(
        self,
        module: GuppyModule,
        hugr_ty: tys.Type,
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
                args: Sequence[GuppyType]
                name: ClassVar[str] = _name

                @staticmethod
                def build(*args: GuppyType, node: AstNode | None = None) -> "GuppyType":
                    # At the moment, custom types don't support type arguments.
                    if len(args) > 0:
                        raise GuppyError(
                            f"Type `{_name}` does not accept type parameters.", node
                        )
                    return NewType([])

                @property
                def type_args(self) -> Iterator[GuppyType]:
                    return iter(self.args)

                @property
                def linear(self) -> bool:
                    return linear

                def to_hugr(self) -> tys.Type:
                    return hugr_ty

                def transform(self, transformer: TypeTransformer) -> GuppyType:
                    return transformer.transform(self) or NewType(
                        [ty.transform(transformer) for ty in self.args]
                    )

                def __str__(self) -> str:
                    return _name

            NewType.__name__ = name
            NewType.__qualname__ = _name
            module.register_type(_name, NewType)
            module._register_buffered_instance_funcs(NewType)
            setattr(c, "_guppy_type", NewType)
            return c

        return dec

    @pretty_errors
    def type_var(self, module: GuppyModule, name: str, linear: bool = False) -> TypeVar:
        """Creates a new type variable in a module."""
        module.register_type_var(name, linear)
        return TypeVar(name)

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

    def take_module(self, id: CallerIdentifier | None = None) -> GuppyModule | None:
        """Returns the local GuppyModule, removing it from the local state."""
        if id is None:
            id = self._get_python_caller()
        if id not in self._modules:
            return None
        module = self._modules[id]
        del self._modules[id]
        return module

    def compile(self, id: CallerIdentifier | None = None) -> Hugr | None:
        """Compiles the local module into a Hugr."""
        module = self.take_module(id)
        return module.compile() if module else None

    def registered_modules(self) -> list[CallerIdentifier]:
        """Returns a list of all currently registered modules for local contexts."""
        return list(self._modules.keys())


guppy = _Guppy()
