import ast
from dataclasses import dataclass, field
from typing import Any, cast

import hugr.build.function as hf
from hugr import Hugr, Wire, val
from hugr.build.dfg import DefinitionBuilder, OpVar

from guppylang.ast_util import AstNode, has_empty_body, with_loc
from guppylang.checker.core import Context, Globals, PyScope
from guppylang.checker.errors.py_errors import (
    PytketSignatureMismatch,
    Tket2NotInstalled,
)
from guppylang.checker.expr_checker import check_call, synthesize_call
from guppylang.checker.func_checker import check_signature
from guppylang.compiler.core import CompiledGlobals, DFContainer
from guppylang.definition.common import (
    CompilableDef,
    ParsableDef,
)
from guppylang.definition.declaration import BodyNotEmptyError
from guppylang.definition.function import (
    PyFunc,
    compile_call,
    load_with_args,
    parse_py_func,
)
from guppylang.definition.ty import TypeDef
from guppylang.definition.value import CallableDef, CallReturnWires, CompiledCallableDef
from guppylang.error import GuppyError, InternalGuppyError
from guppylang.nodes import GlobalCall
from guppylang.span import SourceMap, Span, ToSpan
from guppylang.tys.builtin import bool_type
from guppylang.tys.subst import Inst, Subst
from guppylang.tys.ty import (
    FuncInput,
    FunctionType,
    InputFlags,
    Type,
    row_to_type,
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
    python_scope: PyScope = field(repr=False)
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

        # Compare signatures.
        # TODO: Allow arrays as arguments.
        circuit_signature = _signature_from_circuit(
            self.input_circuit, globals, self.defined_at
        )
        if not (
            circuit_signature.inputs == stub_signature.inputs
            and circuit_signature.output == stub_signature.output
        ):
            # TODO: Implement pretty-printing for signatures in order to add
            # a note for expected vs. actual types.
            raise GuppyError(PytketSignatureMismatch(func_ast, self.name))

        return ParsedPytketDef(
            self.id,
            self.name,
            func_ast,
            stub_signature,
            self.input_circuit,
        )


@dataclass(frozen=True)
class RawLoadPytketDef(ParsableDef):
    """A raw definition for loading pytket circuits without explicit function stub.

    Args:
        id: The unique definition identifier.
        name: The name of the circuit function.
        defined_at: The AST node of the definition (here always None).
        source_span: The source span where the circuit was loaded.
        input_circuit: The user-provided pytket circuit.
    """

    source_span: Span | None
    input_circuit: Any

    description: str = field(default="pytket circuit", init=False)

    def parse(self, globals: Globals, sources: SourceMap) -> "ParsedPytketDef":
        """Creates a function signature based on the user-provided circuit."""
        circuit_signature = _signature_from_circuit(
            self.input_circuit, globals, self.source_span
        )

        return ParsedPytketDef(
            self.id,
            self.name,
            self.defined_at,
            circuit_signature,
            self.input_circuit,
        )


@dataclass(frozen=True)
class ParsedPytketDef(CallableDef, CompilableDef):
    """A circuit definition with signature.

    Args:
        id: The unique definition identifier.
        name: The name of the function.
        defined_at: The AST node of the function stub, if there is one.
        ty: The type of the function.
        input_circuit: The user-provided pytket circuit.
    """

    ty: FunctionType
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
                mapping = module.hugr.insert_hugr(circ)
                hugr_func = mapping[circ.root]

                func_type = self.ty.to_hugr_poly()
                outer_func = module.define_function(
                    self.name, func_type.body.input, func_type.body.output
                )

                # Initialise every input bit in the circuit as false.
                # TODO: Provide the option for the user to pass this input as well.
                bool_wires = [
                    outer_func.load(val.FALSE) for _ in range(self.input_circuit.n_bits)
                ]

                call_node = outer_func.call(
                    hugr_func, *(list(outer_func.inputs()) + bool_wires)
                )
                # Pytket circuit hugr has qubit and bool wires in the opposite order.
                output_list = list(call_node.outputs())
                wires = (
                    output_list[self.input_circuit.n_qubits :]
                    + output_list[: self.input_circuit.n_qubits]
                )
                outer_func.set_outputs(*wires)

        except ImportError:
            pass

        return CompiledPytketDef(
            self.id,
            self.name,
            self.defined_at,
            self.ty,
            self.input_circuit,
            outer_func,
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
        return node, ty


@dataclass(frozen=True)
class CompiledPytketDef(ParsedPytketDef, CompiledCallableDef):
    """A function definition with a corresponding Hugr node.

    Args:
        id: The unique definition identifier.
        name: The name of the function.
        defined_at: The AST node where the function was defined.
        ty: The type of the function.
        input_circuit: The user-provided pytket circuit.
        func_df: The Hugr function definition.
    """

    func_def: hf.Function

    def load_with_args(
        self,
        type_args: Inst,
        dfg: DFContainer,
        globals: CompiledGlobals,
        node: AstNode,
    ) -> Wire:
        """Loads the function as a value into a local Hugr dataflow graph."""
        # Use implementation from function definition.
        return load_with_args(type_args, dfg, self.ty, self.func_def)

    def compile_call(
        self,
        args: list[Wire],
        type_args: Inst,
        dfg: DFContainer,
        globals: CompiledGlobals,
        node: AstNode,
    ) -> CallReturnWires:
        """Compiles a call to the function."""
        # Use implementation from function definition.
        return compile_call(args, type_args, dfg, self.ty, self.func_def)


def _signature_from_circuit(
    input_circuit: Any, globals: Globals, defined_at: ToSpan | None
) -> FunctionType:
    """Helper function for inferring a function signature from a pytket circuit."""
    try:
        import pytket

        if isinstance(input_circuit, pytket.circuit.Circuit):
            try:
                import tket2  # type: ignore[import-untyped, import-not-found, unused-ignore]  # noqa: F401

                qubit = cast(TypeDef, globals["qubit"]).check_instantiate([], globals)

                circuit_signature = FunctionType(
                    [FuncInput(qubit, InputFlags.Inout)] * input_circuit.n_qubits,
                    row_to_type([bool_type()] * input_circuit.n_bits),
                )
            except ImportError:
                err = Tket2NotInstalled(defined_at)
                err.add_sub_diagnostic(Tket2NotInstalled.InstallInstruction(None))
                raise GuppyError(err) from None
        else:
            pass
    except ImportError:
        raise InternalGuppyError(
            "Pytket error should have been caught earlier"
        ) from None
    else:
        return circuit_signature
