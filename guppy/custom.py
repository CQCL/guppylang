import ast
from abc import ABC, abstractmethod
from typing import Optional

from guppy.ast_util import AstNode, get_type, with_loc, with_type
from guppy.checker.core import Context, Globals
from guppy.checker.expr_checker import check_call, synthesize_call
from guppy.checker.func_checker import check_signature
from guppy.compiler.core import CompiledFunction, CompiledGlobals, DFContainer
from guppy.error import (
    GuppyError,
    InternalGuppyError,
    UnknownFunctionType,
)
from guppy.gtypes import FunctionType, GuppyType, type_to_row
from guppy.hugr import ops
from guppy.hugr.hugr import DFContainingVNode, Hugr, Node, OutPortV
from guppy.nodes import GlobalCall


class CustomFunction(CompiledFunction):
    """A function whose type checking and compilation behaviour can be customised."""

    defined_at: Optional[ast.FunctionDef]

    # Whether the function may be used as a higher-order value. This is only possible
    # if a static type for the function is provided.
    higher_order_value: bool

    call_checker: "CustomCallChecker"
    call_compiler: "CustomCallCompiler"

    _ty: Optional[FunctionType] = None
    _defined: dict[Node, DFContainingVNode] = {}

    def __init__(
        self,
        name: str,
        defined_at: Optional[ast.FunctionDef],
        compiler: "CustomCallCompiler",
        checker: "CustomCallChecker",
        higher_order_value: bool = True,
        ty: Optional[FunctionType] = None,
    ):
        self.name = name
        self.defined_at = defined_at
        self.higher_order_value = higher_order_value
        self.call_compiler = compiler
        self.call_checker = checker
        self.used = None
        self._ty = ty
        self._defined = {}

    @property  # type: ignore
    def ty(self) -> FunctionType:
        if self._ty is None:
            return UnknownFunctionType()
        return self._ty

    @ty.setter
    def ty(self, ty: FunctionType) -> None:
        self._ty = ty

    def check_type(self, globals: Globals) -> None:
        """Checks the type annotation on the signature declaration if provided."""
        if self._ty is not None:
            return

        if self.defined_at is None:
            if self.higher_order_value:
                raise GuppyError(
                    f"Type signature for function `{self.name}` is required. "
                    "Alternatively, try passing `higher_order_value=False` on "
                    "definition."
                )
            return

        try:
            self._ty = check_signature(self.defined_at, globals)
        except GuppyError as err:
            # We can ignore the error if a custom call checker is provided and the
            # function may not be used as a higher-order value
            if self.call_checker is None or self.higher_order_value:
                raise err

    def check_call(
        self, args: list[ast.expr], ty: GuppyType, node: AstNode, ctx: Context
    ) -> ast.expr:
        self.call_checker._setup(ctx, node, self)
        return with_type(ty, with_loc(node, self.call_checker.check(args, ty)))

    def synthesize_call(
        self, args: list[ast.expr], node: AstNode, ctx: "Context"
    ) -> tuple[ast.expr, GuppyType]:
        self.call_checker._setup(ctx, node, self)
        new_node, ty = self.call_checker.synthesize(args)
        return with_type(ty, with_loc(node, new_node)), ty

    def compile_call(
        self,
        args: list[OutPortV],
        dfg: DFContainer,
        graph: Hugr,
        globals: CompiledGlobals,
        node: AstNode,
    ) -> list[OutPortV]:
        self.call_compiler._setup(dfg, graph, globals, node)
        return self.call_compiler.compile(args)

    def load(
        self, dfg: "DFContainer", graph: Hugr, globals: CompiledGlobals, node: AstNode
    ) -> OutPortV:
        """Loads the custom function as a value into a local dataflow graph.

        This will place a `FunctionDef` node into the Hugr module if one for this
        function doesn't already exist and loads it into the DFG. This operation will
        fail if no function type has been specified.
        """
        if self._ty is None:
            raise GuppyError(
                "This function does not support usage in a higher-order context",
                node,
            )

        # Find the module node by walking up the hierarchy
        module: Node = dfg.node
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
            _, inp_ports = graph.add_input_with_ports(list(self.ty.args), def_node)
            returns = self.compile_call(
                inp_ports, DFContainer(def_node, {}), graph, globals, node
            )
            graph.add_output(returns, parent=def_node)
            self._defined[module] = def_node

        # Finally, load the function into the local DFG
        return graph.add_load_constant(
            self._defined[module].out_port(0), dfg.node
        ).out_port(0)


class CustomCallChecker(ABC):
    """Protocol for custom function call type checkers."""

    ctx: Context
    node: AstNode
    func: CustomFunction

    def _setup(self, ctx: Context, node: AstNode, func: CustomFunction) -> None:
        self.ctx = ctx
        self.node = node
        self.func = func

    @abstractmethod
    def check(self, args: list[ast.expr], ty: GuppyType) -> ast.expr:
        """Checks the return value against a given type.

        Returns a (possibly) transformed and annotated AST node for the call.
        """

    @abstractmethod
    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, GuppyType]:
        """Synthesizes a type for the return value of a call.

        Also returns a (possibly) transformed and annotated argument list.
        """


class CustomCallCompiler(ABC):
    """Protocol for custom function call compilers."""

    dfg: DFContainer
    graph: Hugr
    globals: CompiledGlobals
    node: AstNode

    def _setup(
        self, dfg: DFContainer, graph: Hugr, globals: CompiledGlobals, node: AstNode
    ) -> None:
        self.dfg = dfg
        self.graph = graph
        self.globals = globals
        self.node = node

    @abstractmethod
    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        """Compiles a custom function call and returns the resulting ports."""


class DefaultCallChecker(CustomCallChecker):
    """Checks function calls by comparing to a type signature."""

    def check(self, args: list[ast.expr], ty: GuppyType) -> ast.expr:
        # Use default implementation from the expression checker
        args = check_call(self.func.ty, args, ty, self.node, self.ctx)
        return GlobalCall(func=self.func, args=args)

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, GuppyType]:
        # Use default implementation from the expression checker
        args, ty = synthesize_call(self.func.ty, args, self.node, self.ctx)
        return GlobalCall(func=self.func, args=args), ty


class DefaultCallCompiler(CustomCallCompiler):
    """Call compiler that invokes the regular expression compiler."""

    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        raise NotImplementedError


class OpCompiler(CustomCallCompiler):
    op: ops.OpType

    def __init__(self, op: ops.OpType) -> None:
        self.op = op

    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        node = self.graph.add_node(self.op.copy(), inputs=args, parent=self.dfg.node)
        return_ty = get_type(self.node)
        return [node.add_out_port(ty) for ty in type_to_row(return_ty)]


class NoopCompiler(CustomCallCompiler):
    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        return args
