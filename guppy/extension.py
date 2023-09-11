import ast
import builtins
import inspect
import textwrap
from dataclasses import dataclass, field
from types import ModuleType
from typing import Optional, Callable, Any, Union, Sequence

from guppy.ast_util import AstNode
from guppy.compiler_base import GlobalFunction, TypeName, Globals, CallCompiler, \
    ValueName
from guppy.error import GuppyError, InternalGuppyError
from guppy.expression import type_check_call
from guppy.function import FunctionDefCompiler
from guppy.guppy_types import FunctionType, GuppyType
from guppy.hugr import ops, tys as tys
from guppy.hugr.hugr import Hugr, DFContainingNode, OutPortV, Node, DFContainingVNode


class ExtensionDefinitionError(Exception):
    """Exception indicating a failure while defining an extension."""

    def __init__(self, msg: str, extension: "GuppyExtension") -> None:
        super().__init__(
            f"Definition of extension `{extension.name}` is invalid: {msg}"
        )


@dataclass
class ExtensionFunction(GlobalFunction):
    """A custom function to extend Guppy with functionality.

    Must be provided with a `CallCompiler` that handles compilation of calls to the
    extension function. This allows for full flexibility in how extensions are compiled.
    Additionally, it can be specified whether the function can be used as a value in a
    higher-order context.
    """

    call_compiler: CallCompiler
    higher_order: bool = True

    _defined: dict[Node, DFContainingVNode] = field(default_factory=dict, init=False)

    def load(self, graph: Hugr, parent: DFContainingNode, globals: Globals, node: AstNode) -> OutPortV:
        """Loads the extension function as a value into a local dataflow graph.

        This will place a `FunctionDef` node into the Hugr module if one for this
        function doesn't already exist and loads it into the DFG. This operation will
        fail of the extension function is marked as not supporting higher-order usage.
        """
        if not self.higher_order:
            raise GuppyError(
                "This function does not support usage in a higher-order context",
                node,
            )

        # Find the module node by walking up the hierarchy
        module: Node = parent
        while not isinstance(module.op, ops.Module):
            if module.parent is None:
                raise InternalGuppyError(
                    "Encountered node that is not contained in a module."
                )
            module = module.parent

        # If the function has not yet been loaded in this module, we first have to
        # define it. We create a `FunctionDef` that takes some inputs, compiles a call
        # to the function, and returns the results.
        if module not in self._defined:
            def_node = graph.add_def(self.ty, module, self.name)
            inp = graph.add_input(list(self.ty.args), parent=def_node)
            returns = self.compile_call(
                [inp.out_port(i) for i in range(len(self.ty.args))],
                def_node,
                graph,
                globals,
                node,
            )
            graph.add_output(returns, parent=def_node)
            self._defined[module] = def_node

        # Finally, load the function into the local DFG
        return graph.add_load_constant(
            self._defined[module].out_port(0), parent
        ).out_port(0)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        raise GuppyError("Tried to call Guppy function in a Python context")


class UntypedExtensionFunction(ExtensionFunction):
    """An extension function that does not require a signature.

    As a result, functions like this cannot be used in a higher-order context.
    """

    def __init__(self, name: str, defined_at: Optional[AstNode], call_compiler: CallCompiler):
        self.name = name
        self.defined_at = defined_at
        self.higher_order = False
        self.call_compiler = call_compiler

    @property  # type: ignore
    def ty(self) -> FunctionType:
        raise InternalGuppyError(
            "Tried to access signature from untyped extension function"
        )


class GuppyExtension:
    """A Guppy extension.

    Consists of a collection of types, extension functions, and instance functions.
    Note that extensions can also declare instance functions for types that are not
    defined in this extension.
    """

    name: str
    types: dict[TypeName, type[GuppyType]]
    funcs: dict[ValueName, "ExtensionFunction"]
    instance_funcs: dict[tuple[TypeName, ValueName], "ExtensionFunction"]

    _globals: Globals
    _type_alias_map: dict[str, TypeName]

    def __init__(self, name: str, dependencies: Sequence[ModuleType]) -> None:
        """Creates a new empty Guppy extension.

        If the extension uses types from other extensions (for example the `builtin.py`
        extensions from the prelude), they have to passed as dependencies.
        """

        self.name = name
        self.types = {}
        self.funcs = {}
        self.instance_funcs = {}
        self._globals = Globals.default()
        self._type_alias_map = {}

        for module in dependencies:
            exts = [obj for obj in module.__dict__.values() if isinstance(obj, GuppyExtension)]
            if len(exts) == 0:
                raise ExtensionDefinitionError(
                    f"Dependency module `{module.__name__}` does not contain a Guppy extension",
                    self,
                )
            for ext in exts:
                ext.add_to_globals(self._globals)

    def add_to_globals(self, globals: Globals) -> None:
        globals.types.update(self.types)
        globals.values.update(self.funcs)
        globals.instance_funcs.update(self.instance_funcs)

    def register_type(self, name: str, ty: type[GuppyType]) -> None:
        self.types[name] = ty
        self._globals.types[name] = ty

    def register_func(self, name: str, func: "ExtensionFunction") -> None:
        self.funcs[name] = func

    def register_instance_func(
        self, ty: type[GuppyType], name: str, func: "ExtensionFunction"
    ) -> None:
        self.instance_funcs[ty.name, name] = func

    def new_type(
        self, name: str, hugr_repr: tys.SimpleType, linear: bool = False
    ) -> type[GuppyType]:
        _name = name

        class NewType(GuppyType):
            name = _name

            @staticmethod
            def build(
                *args: GuppyType, node: Union[ast.Name, ast.Subscript]
            ) -> "GuppyType":
                return NewType()

            @property
            def linear(self) -> bool:
                return linear

            def to_hugr(self) -> tys.SimpleType:
                return hugr_repr

            def __eq__(self, other: Any) -> bool:
                return isinstance(other, NewType)

            def __str__(self) -> str:
                return name

        self._type_alias_map[NewType.__name__] = name
        NewType.__name__ = NewType.__qualname__ = name
        self.register_type(name, NewType)
        return NewType

    def type(
        self,
        hugr_repr: tys.SimpleType,
        alias: Optional[str] = None,
        linear: bool = False,
    ) -> Callable[[type], type]:
        def decorator(cls: type) -> type:
            self.new_type(alias or cls.__name__, hugr_repr, linear)
            return cls  # TODO: Return class or new_type ??

        return decorator

    def new_func(
        self,
        name: str,
        call_compiler: CallCompiler,
        signature: Optional[FunctionType] = None,
        higher_order: bool = True,
        instance: Optional[builtins.type[GuppyType]] = None,
    ) -> ExtensionFunction:
        func: ExtensionFunction
        if signature is None:
            if higher_order:
                raise ExtensionDefinitionError(
                    "Signature may only be omitted if `higher_order=False` is set",
                    self,
                )
            func = UntypedExtensionFunction(name, None, call_compiler)  # TODO: Location
        else:
            func = ExtensionFunction(
                name, signature, None, call_compiler, higher_order  # TODO: Location
            )
        if instance is not None:
            self.register_instance_func(instance, name, func)
        else:
            self.register_func(name, func)

        return func

    def func(
        self,
        call_compiler: CallCompiler,
        alias: Optional[str] = None,
        higher_order: bool = True,
        instance: Optional[builtins.type[GuppyType]] = None,
    ) -> Callable[[Callable[..., Any]], ExtensionFunction]:
        def decorator(f: Callable[..., Any]) -> ExtensionFunction:
            # Check if f was defined in a class. In that case, the qualified name of f
            # would be `ContainingClass.func_name`.
            qualname = f.__qualname__.split(".")
            inst: Optional[type[GuppyType]]
            if len(qualname) == 2 and qualname[0] in self._type_alias_map:
                inst = self.types[self._type_alias_map[qualname[0]]]
            else:
                inst = instance

            func_ast, ty = self._parse_decl(f)
            name = alias or func_ast.name
            return self.new_func(name, call_compiler, ty, higher_order, inst)

        return decorator

    def _parse_decl(
        self, f: Callable[..., Any]
    ) -> tuple[ast.FunctionDef, Optional[FunctionType]]:
        source = textwrap.dedent(inspect.getsource(f))
        func_ast = ast.parse(source).body[0]
        if not isinstance(func_ast, ast.FunctionDef):
            raise ExtensionDefinitionError(
                "Only functions may be annotated using `@extension`", self
            )
        if len(func_ast.body) > 0:
            b = func_ast.body[0]
            is_pass = isinstance(b, ast.Ellipsis)
            is_ellipsis = isinstance(b, ast.Expr) and isinstance(b.value, ast.Ellipsis)
            if len(func_ast.body) > 1 or not (is_pass or is_ellipsis):
                raise ExtensionDefinitionError(
                    "Body of declared extension functions must be empty", self
                )
        # Return None if annotations are missing
        if not func_ast.returns or not all(arg.annotation for arg in func_ast.args.args):
            return func_ast, None

        return func_ast, FunctionDefCompiler.validate_signature(func_ast, self._globals)


class OpCompiler(CallCompiler):
    op: ops.OpType
    signature: Optional[FunctionType] = None

    def __init__(self, op: ops.OpType, signature: Optional[FunctionType] = None):
        self.op = op
        self.signature = signature

    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        func_ty = self.signature or self.func.ty
        type_check_call(func_ty, args, self.node)
        leaf = self.graph.add_node(self.op.copy(), inputs=args, parent=self.parent)
        return [leaf.add_out_port(ty) for ty in func_ty.returns]


class NoopCompiler(CallCompiler):
    type_check: bool

    def __init__(self, type_check: bool = True):
        self.type_check = type_check

    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        if self.type_check:
            func_ty = self.func.ty
            type_check_call(func_ty, args, self.node)
        return args


class Reversed(CallCompiler):
    cc: CallCompiler

    def __init__(self, cc: CallCompiler):
        self.cc = cc

    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        self.cc.parent = self.parent
        self.cc.graph = self.graph
        self.cc.globals = self.globals
        self.cc.node = self.node
        return self.cc.compile(list(reversed(args)))


class NotImplementedCompiler(CallCompiler):
    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        raise GuppyError("Operation is not yet implemented")
