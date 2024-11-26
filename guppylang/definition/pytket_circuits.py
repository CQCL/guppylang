import ast
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, cast

from hugr import Hugr, Wire, ops
import hugr.build.function as hf
import hugr.tys as ht
from hugr.build.dfg import DefinitionBuilder, OpVar

from guppylang.ast_util import AstNode, with_loc
from guppylang.checker.expr_checker import check_call, synthesize_call
from guppylang.ast_util import has_empty_body
from guppylang.checker.core import Context, Globals, PyScope
from guppylang.checker.func_checker import check_signature
from guppylang.compiler.core import CompiledGlobals, DFContainer
from guppylang.definition.common import (
    CompilableDef,
    ParsableDef,
)
from guppylang.definition.value import CallReturnWires, CallableDef
from guppylang.definition.declaration import BodyNotEmptyError
from guppylang.definition.function import CheckedFunctionDef, CompiledFunctionDef, PyFunc, parse_py_func
from guppylang.definition.ty import TypeDef
from guppylang.definition.value import CompiledCallableDef
from guppylang.span import SourceMap

from guppylang.checker.errors.py_errors import (
    PytketSignatureMismatch,
    Tket2NotInstalled,
    PytketNotCircuit
)
from guppylang.error import GuppyError
from guppylang.nodes import GlobalCall
from guppylang.tys.builtin import bool_type
from guppylang.tys.subst import Inst, Subst
from guppylang.tys.ty import (
    FuncInput,
    FunctionType,
    Type,
    InputFlags,
    row_to_type,
    type_to_row,
)


@dataclass(frozen=True)
class RawPytketDef(ParsableDef):
    """A raw function stub definition describing the signature of a circuit.

    Args:
        id: The unique definition identifier.
        name: The name of the function stub.
        defined_at: The AST node where the stub was defined.
        python_func: The Python function stub.
        python_scope: The Python scope where the function stub was defined.
        input_circuit: The user-provided pytket circuit.
    """

    python_func: PyFunc
    python_scope: PyScope
    input_circuit: Any

    description: str = field(default="pytket circuit", init=False)

    def parse(self, globals: Globals, sources: SourceMap) -> "ParsedPytketDef":
        """Parses and checks the user-provided signature matches the user-provided
        circuit.
        """
        # Retrieve stub signature.
        func_ast, _ = parse_py_func(self.python_func, sources)
        if not has_empty_body(func_ast):
            # Function stub should have empty body.
            raise GuppyError(BodyNotEmptyError(func_ast.body[0], self.name))
        stub_signature = check_signature(
            func_ast, globals.with_python_scope(self.python_scope)
        )

        # Retrieve circuit signature and compare.
        try:
            import pytket

            if isinstance(self.input_circuit, pytket.circuit.Circuit):
                try:
                    import tket2  # type: ignore[import-untyped, import-not-found, unused-ignore]  # noqa: F401

                    qubit = cast(TypeDef, globals["qubit"]).check_instantiate(
                        [], globals
                    )
                    circuit_signature = FunctionType(
                        [FuncInput(qubit, InputFlags.Inout)]
                        * self.input_circuit.n_qubits,
                        row_to_type([bool_type()] * self.input_circuit.n_bits),
                    )
                    # TODO: Allow arrays in stub signature.
                    if not (
                        circuit_signature.inputs == stub_signature.inputs
                        and circuit_signature.output == stub_signature.output
                    ):
                        raise GuppyError(
                            PytketSignatureMismatch(func_ast, self.name)
                        )
                except ImportError:
                    err = Tket2NotInstalled(func_ast)
                    err.add_sub_diagnostic(Tket2NotInstalled.InstallInstruction(None))
                    raise GuppyError(err) from None
            else:
                raise GuppyError(PytketNotCircuit(func_ast))
        except ImportError:
            pass
        return ParsedPytketDef(
            self.id,
            self.name,
            func_ast,
            stub_signature,
            self.python_scope,
            self.input_circuit,
        )


@dataclass(frozen=True)
class ParsedPytketDef(CallableDef, CompilableDef):
    """A circuit definition with parsed and checked signature.

    Args:
        id: The unique definition identifier.
        name: The name of the function.
        defined_at: The AST node where the function was defined.
        ty: The type of the function.
        python_scope: The Python scope where the function was defined.
        input_circuit: The user-provided pytket circuit.
    """

    defined_at: ast.FunctionDef
    ty: FunctionType
    python_scope: PyScope
    input_circuit: Any

    description: str = field(default="pytket circuit", init=False)

    def compile_outer(self, module: DefinitionBuilder[OpVar]) -> "CompiledPytketDef":
        """Adds a Hugr `FuncDefn` node for this function to the Hugr."""

        try:
            import pytket

            if isinstance(self.input_circuit, pytket.circuit.Circuit):
                from tket2.circuit import (  # type: ignore[import-untyped, import-not-found, unused-ignore]
                    Tk2Circuit,
                )
                circ = Hugr.load_json(Tk2Circuit(self.input_circuit).to_hugr_json())  # type: ignore[attr-defined, unused-ignore]
                print(circ)
            else:
                raise GuppyError(PytketNotCircuit(self.defined_at))
        except ImportError:
            pass

        hugr_func = None
        return CompiledPytketDef(self.id, self.name, self.defined_at, self.ty, self.python_scope, None, None, hugr_func)
    
        
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
        return node, ty


@dataclass(frozen=True)
class CompiledPytketDef(CompiledFunctionDef, CompiledCallableDef):
    """A function definition with a corresponding Hugr node.

    Args:
        id: The unique definition identifier.
        name: The name of the function.
        defined_at: The AST node where the function was defined.
        ty: The type of the function.
        python_scope: The Python scope where the function was defined.
        func_df: The Hugr function definition.
    """

    func_def: hf.Function

    def compile_inner(self, globals: CompiledGlobals) -> None:
        pass
