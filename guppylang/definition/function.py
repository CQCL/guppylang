import ast
import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import hugr.build.function as hf
import hugr.tys as ht
from hugr import Wire
from hugr.build.dfg import DefinitionBuilder, OpVar
from hugr.hugr.node_port import ToNode
from hugr.package import FuncDefnPointer

from guppylang.ast_util import AstNode, annotate_location, with_loc, with_type
from guppylang.checker.cfg_checker import CheckedCFG
from guppylang.checker.core import Context, Globals, Place, PyScope
from guppylang.checker.errors.generic import ExpectedError
from guppylang.checker.expr_checker import check_call, synthesize_call
from guppylang.checker.func_checker import (
    check_global_func_def,
    check_signature,
    parse_function_with_docstring,
)
from guppylang.compiler.core import CompilerContext, DFContainer
from guppylang.compiler.func_compiler import compile_global_func_def
from guppylang.definition.common import (
    CheckableDef,
    CompilableDef,
    ParsableDef,
    UnknownSourceError,
)
from guppylang.definition.value import CallableDef, CallReturnWires, CompiledCallableDef
from guppylang.error import GuppyError
from guppylang.ipython_inspect import find_ipython_def, is_running_ipython
from guppylang.nodes import GlobalCall
from guppylang.span import SourceMap
from guppylang.tys.subst import Inst, Subst
from guppylang.tys.ty import FunctionType, Type, type_to_row

PyFunc = Callable[..., Any]


@dataclass(frozen=True)
class RawFunctionDef(ParsableDef):
    """A raw function definition provided by the user.

    The raw definition stores exactly what the user has written (i.e. the AST), without
    any additional checking or parsing. Furthermore, we store the values of the Python
    variables in scope at the point of definition.

    Args:
        id: The unique definition identifier.
        name: The name of the function.
        defined_at: The AST node where the function was defined.
        python_func: The Python function to be defined.
        python_scope: The Python scope where the function was defined.
    """

    python_func: PyFunc
    python_scope: PyScope = field(repr=False)

    description: str = field(default="function", init=False)

    def parse(self, globals: Globals, sources: SourceMap) -> "ParsedFunctionDef":
        """Parses and checks the user-provided signature of the function."""
        func_ast, docstring = parse_py_func(self.python_func, sources)
        ty = check_signature(func_ast, globals.with_python_scope(self.python_scope))
        return ParsedFunctionDef(
            self.id, self.name, func_ast, ty, self.python_scope, docstring
        )

    def compile(self) -> FuncDefnPointer:
        from guppylang.decorator import guppy

        return guppy.compile_function(self)


@dataclass(frozen=True)
class ParsedFunctionDef(CheckableDef, CallableDef):
    """A function definition with parsed and checked signature.

    In particular, this means that we have determined a type for the function and are
    ready to check the function body.

    Args:
        id: The unique definition identifier.
        name: The name of the function.
        defined_at: The AST node where the function was defined.
        ty: The type of the function.
        python_scope: The Python scope where the function was defined.
        docstring: The docstring of the function.
    """

    python_scope: PyScope = field(repr=False)
    defined_at: ast.FunctionDef
    ty: FunctionType
    docstring: str | None

    description: str = field(default="function", init=False)

    def check(self, globals: Globals) -> "CheckedFunctionDef":
        """Type checks the body of the function."""
        # Add python variable scope to the globals
        globals = globals.with_python_scope(self.python_scope)
        cfg = check_global_func_def(self.defined_at, self.ty, globals)
        return CheckedFunctionDef(
            self.id,
            self.name,
            self.defined_at,
            self.ty,
            self.python_scope,
            self.docstring,
            cfg,
        )

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
    ) -> tuple[ast.expr, Type]:
        """Synthesizes the return type of a function call."""
        # Use default implementation from the expression checker
        args, ty, inst = synthesize_call(self.ty, args, node, ctx)
        node = with_loc(node, GlobalCall(def_id=self.id, args=args, type_args=inst))
        return with_type(ty, node), ty


@dataclass(frozen=True)
class CheckedFunctionDef(ParsedFunctionDef, CompilableDef):
    """Type checked version of a user-defined function that is ready to be compiled.

    In particular, this means that we have a constructed and type checked a control-flow
    graph for the function body.

    Args:
        id: The unique definition identifier.
        name: The name of the function.
        defined_at: The AST node where the function was defined.
        ty: The type of the function.
        python_scope: The Python scope where the function was defined.
        docstring: The docstring of the function.
        cfg: The type- and linearity-checked CFG for the function body.
    """

    cfg: CheckedCFG[Place]

    def compile_outer(self, module: DefinitionBuilder[OpVar]) -> "CompiledFunctionDef":
        """Adds a Hugr `FuncDefn` node for this function to the Hugr.

        Note that we don't compile the function body at this point since we don't have
        access to the other compiled functions yet. The body is compiled later in
        `CompiledFunctionDef.compile_inner()`.
        """
        func_type = self.ty.to_hugr_poly()
        func_def = module.define_function(
            self.name, func_type.body.input, func_type.body.output, func_type.params
        )
        return CompiledFunctionDef(
            self.id,
            self.name,
            self.defined_at,
            self.ty,
            self.python_scope,
            self.docstring,
            self.cfg,
            func_def,
        )


@dataclass(frozen=True)
class CompiledFunctionDef(CheckedFunctionDef, CompiledCallableDef):
    """A function definition with a corresponding Hugr node.

    Args:
        id: The unique definition identifier.
        name: The name of the function.
        defined_at: The AST node where the function was defined.
        ty: The type of the function.
        python_scope: The Python scope where the function was defined.
        docstring: The docstring of the function.
        cfg: The type- and linearity-checked CFG for the function body.
        func_def: The Hugr function definition.
    """

    func_def: hf.Function

    def load_with_args(
        self,
        type_args: Inst,
        dfg: DFContainer,
        ctx: CompilerContext,
        node: AstNode,
    ) -> Wire:
        """Loads the function as a value into a local Hugr dataflow graph."""
        return load_with_args(type_args, dfg, self.ty, self.func_def)

    def compile_call(
        self,
        args: list[Wire],
        type_args: Inst,
        dfg: DFContainer,
        ctx: CompilerContext,
        node: AstNode,
    ) -> CallReturnWires:
        """Compiles a call to the function."""
        return compile_call(args, type_args, dfg, self.ty, self.func_def)

    def compile_inner(self, globals: CompilerContext) -> None:
        """Compiles the body of the function."""
        compile_global_func_def(self, self.func_def, globals)


def load_with_args(
    type_args: Inst,
    dfg: DFContainer,
    ty: FunctionType,
    func: ToNode,
) -> Wire:
    """Loads the function as a value into a local Hugr dataflow graph."""
    func_ty: ht.FunctionType = ty.instantiate(type_args).to_hugr()
    type_args: list[ht.TypeArg] = [arg.to_hugr() for arg in type_args]
    return dfg.builder.load_function(func, func_ty, type_args)


def compile_call(
    args: list[Wire],
    type_args: Inst,
    dfg: DFContainer,
    ty: FunctionType,
    func: ToNode,
) -> CallReturnWires:
    """Compiles a call to the function."""
    func_ty: ht.FunctionType = ty.instantiate(type_args).to_hugr()
    type_args: list[ht.TypeArg] = [arg.to_hugr() for arg in type_args]
    num_returns = len(type_to_row(ty.output))
    call = dfg.builder.call(func, *args, instantiation=func_ty, type_args=type_args)
    return CallReturnWires(
        regular_returns=list(call[:num_returns]),
        inout_returns=list(call[num_returns:]),
    )


def parse_py_func(f: PyFunc, sources: SourceMap) -> tuple[ast.FunctionDef, str | None]:
    source_lines, line_offset = inspect.getsourcelines(f)
    source, func_ast, line_offset = parse_source(source_lines, line_offset)
    # In Jupyter notebooks, we shouldn't use `inspect.getsourcefile(f)` since it would
    # only give us a dummy temporary file
    file: str | None
    if is_running_ipython():
        file = "<In [?]>"
        if isinstance(func_ast, ast.FunctionDef):
            defn = find_ipython_def(func_ast.name)
            if defn is not None:
                file = f"<{defn.cell_name}>"
                sources.add_file(file, defn.cell_source)
            else:
                # If we couldn't find the defining cell, just use the source code we
                # got from inspect. Line numbers will be wrong, but that's the best we
                # can do.
                sources.add_file(file, source)
                line_offset = 0
    else:
        file = inspect.getsourcefile(f)
        if file is None:
            raise GuppyError(UnknownSourceError(None, f))
        sources.add_file(file)
    annotate_location(func_ast, source, file, line_offset)
    if not isinstance(func_ast, ast.FunctionDef):
        raise GuppyError(ExpectedError(func_ast, "a function definition"))
    return parse_function_with_docstring(func_ast)


def parse_source(source_lines: list[str], line_offset: int) -> tuple[str, ast.AST, int]:
    """Parses a list of source lines into an AST object.

    Also takes care of correctly parsing source that is indented.

    Returns the full source, the parsed AST node, and a potentially updated line number
    offset.
    """
    source = "".join(source_lines)  # Lines already have trailing \n's
    if source_lines[0][0].isspace():
        # This means the function is indented, so we cannot parse it straight away.
        # Running `textwrap.dedent` would mess up the column number in spans. Instead,
        # we'll just wrap the source into a dummy class definition so the indent becomes
        # valid
        cls_node = ast.parse("class _:\n" + source).body[0]
        assert isinstance(cls_node, ast.ClassDef)
        node = cls_node.body[0]
        line_offset -= 1
    else:
        node = ast.parse(source).body[0]
    return source, node, line_offset
