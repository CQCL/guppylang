import ast
from dataclasses import dataclass, field

from hugr import Node, Wire
from hugr import function as hf
from hugr import tys as ht
from hugr.dfg import OpVar, _DefinitionBuilder

from guppylang.ast_util import AstNode, has_empty_body, with_loc
from guppylang.checker.core import Context, Globals
from guppylang.checker.expr_checker import check_call, synthesize_call
from guppylang.checker.func_checker import check_signature
from guppylang.compiler.core import CompiledGlobals, DFContainer
from guppylang.definition.common import CompilableDef, ParsableDef
from guppylang.definition.function import PyFunc, parse_py_func
from guppylang.definition.value import CallableDef, CallReturnWires, CompiledCallableDef
from guppylang.error import GuppyError
from guppylang.nodes import GlobalCall
from guppylang.tys.subst import Inst, Subst
from guppylang.tys.ty import Type, type_to_row


@dataclass(frozen=True)
class RawFunctionDecl(ParsableDef):
    """A raw function declaration provided by the user.

    The raw declaration stores exactly what the user has written (i.e. the AST), without
    any additional checking or parsing.
    """

    python_func: PyFunc
    description: str = field(default="function", init=False)

    def parse(self, globals: Globals) -> "CheckedFunctionDecl":
        """Parses and checks the user-provided signature of the function."""
        func_ast, docstring = parse_py_func(self.python_func)
        ty = check_signature(func_ast, globals)
        if not has_empty_body(func_ast):
            raise GuppyError(
                "Body of function declaration must be empty", func_ast.body[0]
            )
        return CheckedFunctionDecl(
            self.id, self.name, func_ast, ty, self.python_func, docstring
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
        return node, ty

    def compile_outer(
        self, module: _DefinitionBuilder[OpVar]
    ) -> "CompiledFunctionDecl":
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
        globals: CompiledGlobals,
        node: AstNode,
    ) -> Wire:
        """Loads the function as a value into a local Hugr dataflow graph."""
        func_ty: ht.FunctionType = self.ty.instantiate(type_args).to_hugr()
        type_args: list[ht.TypeArg] = [arg.to_hugr() for arg in type_args]
        return dfg.builder.load_function(self.declaration, func_ty, type_args)

    def compile_call(
        self,
        args: list[Wire],
        type_args: Inst,
        dfg: DFContainer,
        globals: CompiledGlobals,
        node: AstNode,
    ) -> CallReturnWires:
        """Compiles a call to the function."""
        func_ty: ht.FunctionType = self.ty.instantiate(type_args).to_hugr()
        type_args: list[ht.TypeArg] = [arg.to_hugr() for arg in type_args]
        num_returns = len(type_to_row(self.ty.output))
        call = dfg.builder.call(
            self.declaration, *args, instantiation=func_ty, type_args=type_args
        )
        return CallReturnWires(
            # TODO: Replace below with `list(call[:num_returns])` once
            #  https://github.com/CQCL/hugr/issues/1454 is fixed.
            regular_returns=[call[i] for i in range(num_returns)],
            inout_returns=list(call[num_returns:]),
        )
