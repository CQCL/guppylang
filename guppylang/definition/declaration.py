import ast
from dataclasses import dataclass, field
from typing import ClassVar

from hugr import Node, Wire
from hugr.build import function as hf
from hugr.build.dfg import DefinitionBuilder, OpVar

from guppylang.ast_util import AstNode, has_empty_body, with_loc, with_type
from guppylang.checker.core import Context, Globals, PyScope
from guppylang.checker.expr_checker import check_call, synthesize_call
from guppylang.checker.func_checker import check_signature
from guppylang.compiler.core import CompilerContext, DFContainer
from guppylang.definition.common import CompilableDef, ParsableDef
from guppylang.definition.function import (
    PyFunc,
    compile_call,
    load_with_args,
    parse_py_func,
)
from guppylang.definition.value import CallableDef, CallReturnWires, CompiledCallableDef
from guppylang.diagnostic import Error
from guppylang.error import GuppyError
from guppylang.nodes import GlobalCall
from guppylang.span import SourceMap
from guppylang.tys.subst import Inst, Subst
from guppylang.tys.ty import Type


@dataclass(frozen=True)
class BodyNotEmptyError(Error):
    title: ClassVar[str] = "Unexpected function body"
    span_label: ClassVar[str] = "Body of declared function `{name}` must be empty"
    name: str


@dataclass(frozen=True)
class RawFunctionDecl(ParsableDef):
    """A raw function declaration provided by the user.

    The raw declaration stores exactly what the user has written (i.e. the AST), without
    any additional checking or parsing.
    """

    python_func: PyFunc
    python_scope: PyScope = field(repr=False)
    description: str = field(default="function", init=False)

    def parse(self, globals: Globals, sources: SourceMap) -> "CheckedFunctionDecl":
        """Parses and checks the user-provided signature of the function."""
        func_ast, docstring = parse_py_func(self.python_func, sources)
        ty = check_signature(func_ast, globals.with_python_scope(self.python_scope))
        if not has_empty_body(func_ast):
            raise GuppyError(BodyNotEmptyError(func_ast.body[0], self.name))
        return CheckedFunctionDecl(
            self.id,
            self.name,
            func_ast,
            ty,
            self.python_func,
            self.python_scope,
            docstring,
        )


@dataclass(frozen=True)
class CheckedFunctionDecl(RawFunctionDecl, CompilableDef, CallableDef):
    """A function declaration with parsed and checked signature.

    In particular, this means that we have determined a type for the function.
    """

    defined_at: ast.FunctionDef
    docstring: str | None

    def check_call(
        self, args: list[ast.expr], ty: Type, node: AstNode, ctx: Context
    ) -> tuple[ast.expr, Subst]:
        """Checks the return type of a function call against a given type."""
        # Use default implementation from the expression checker
        args, subst, inst = check_call(self.ty, args, ty, node, ctx)
        node = with_loc(node, GlobalCall(def_id=self.id, args=args, type_args=inst))
        return node, subst

    def synthesize_call(
        self, args: list[ast.expr], node: AstNode, ctx: Context
    ) -> tuple[GlobalCall, Type]:
        """Synthesizes the return type of a function call."""
        # Use default implementation from the expression checker
        args, ty, inst = synthesize_call(self.ty, args, node, ctx)
        node = with_loc(node, GlobalCall(def_id=self.id, args=args, type_args=inst))
        return with_type(ty, node), ty

    def compile_outer(self, module: DefinitionBuilder[OpVar]) -> "CompiledFunctionDecl":
        """Adds a Hugr `FuncDecl` node for this function to the Hugr."""
        assert isinstance(
            module, hf.Module
        ), "Functions can only be declared in modules"
        module: hf.Module = module

        node = module.declare_function(self.name, self.ty.to_hugr_poly())
        return CompiledFunctionDecl(
            self.id,
            self.name,
            self.defined_at,
            self.ty,
            self.python_func,
            self.python_scope,
            self.docstring,
            node,
        )


@dataclass(frozen=True)
class CompiledFunctionDecl(CheckedFunctionDecl, CompiledCallableDef):
    """A function declaration with a corresponding Hugr node."""

    declaration: Node

    def load_with_args(
        self,
        type_args: Inst,
        dfg: DFContainer,
        ctx: CompilerContext,
        node: AstNode,
    ) -> Wire:
        """Loads the function as a value into a local Hugr dataflow graph."""
        # Use implementation from function definition.
        return load_with_args(type_args, dfg, self.ty, self.declaration)

    def compile_call(
        self,
        args: list[Wire],
        type_args: Inst,
        dfg: DFContainer,
        ctx: CompilerContext,
        node: AstNode,
    ) -> CallReturnWires:
        """Compiles a call to the function."""
        # Use implementation from function definition.
        return compile_call(args, type_args, dfg, self.ty, self.declaration)
