import ast
from dataclasses import dataclass, field
from typing import Any, cast

import hugr.build.function as hf
from hugr import Hugr, Wire, ops, val
from hugr import tys as ht
from hugr.build.dfg import DefinitionBuilder, OpVar

from guppylang.ast_util import AstNode, has_empty_body, with_loc
from guppylang.checker.core import Context, Globals, PyScope
from guppylang.checker.errors.comptime_errors import (
    PytketSignatureMismatch,
    Tket2NotInstalled,
)
from guppylang.checker.expr_checker import check_call, synthesize_call
from guppylang.checker.func_checker import check_signature
from guppylang.compiler.core import CompilerContext, DFContainer
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
from guppylang.std._internal.compiler.array import (
    array_discard_empty,
    array_new,
    array_pop,
)
from guppylang.std._internal.compiler.prelude import build_unwrap
from guppylang.tys.builtin import array_type, bool_type
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
        circuit_signature = _signature_from_circuit(
            self.input_circuit, globals, self.defined_at
        )
        if not (
            circuit_signature.inputs == stub_signature.inputs
            and circuit_signature.output == stub_signature.output
        ):
            err = PytketSignatureMismatch(func_ast, self.name)
            err.add_sub_diagnostic(
                PytketSignatureMismatch.TypeHint(None, circ_sig=circuit_signature)
            )
            raise GuppyError(err)
        return ParsedPytketDef(
            self.id, self.name, func_ast, stub_signature, self.input_circuit, False
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
        use_arrays: Whether the circuit function should use arrays as input types.
    """

    source_span: Span | None
    input_circuit: Any
    use_arrays: bool

    description: str = field(default="pytket circuit", init=False)

    def parse(self, globals: Globals, sources: SourceMap) -> "ParsedPytketDef":
        """Creates a function signature based on the user-provided circuit."""
        circuit_signature = _signature_from_circuit(
            self.input_circuit, globals, self.source_span, self.use_arrays
        )

        return ParsedPytketDef(
            self.id,
            self.name,
            self.defined_at,
            circuit_signature,
            self.input_circuit,
            self.use_arrays,
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
        use_arrays: Whether the circuit function should use arrays as input types.
    """

    ty: FunctionType
    input_circuit: Any
    use_arrays: bool

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

                input_list = []
                if self.use_arrays:
                    # If the input is given as arrays, we need to unpack each element in
                    # them into separate wires.
                    # TODO: Replace with actual unpack HUGR op once
                    # https://github.com/CQCL/hugr/issues/1947 is done.
                    def unpack(
                        array: Wire, elem_ty: ht.Type, length: int
                    ) -> list[Wire]:
                        err = "Internal error: unpacking of array failed"
                        elts: list[Wire] = []
                        for i in range(length):
                            res = outer_func.add_op(
                                array_pop(elem_ty, length - i, True), array
                            )
                            [elt_opt, array] = build_unwrap(outer_func, res, err)
                            [elt] = build_unwrap(outer_func, elt_opt, err)
                            elts.append(elt)
                        outer_func.add_op(array_discard_empty(elem_ty), array)
                        return elts

                    # Must be same length due to earlier signature computation /
                    # comparison.
                    for q_reg, wire in zip(
                        self.input_circuit.q_registers,
                        list(outer_func.inputs()),
                        strict=True,
                    ):
                        input_list.extend(unpack(wire, ht.Option(ht.Qubit), q_reg.size))

                else:
                    # Otherwise pass inputs directly.
                    input_list = list(outer_func.inputs())

                call_node = outer_func.call(hugr_func, *(input_list + bool_wires))

                # Pytket circuit hugr has qubit and bool wires in the opposite
                # order to Guppy output wires.
                output_list: list[Wire] = list(call_node.outputs())
                wires = (
                    output_list[self.input_circuit.n_qubits :]
                    + output_list[: self.input_circuit.n_qubits]
                )

                if self.use_arrays:

                    def pack(elems: list[Wire], elem_ty: ht.Type, length: int) -> Wire:
                        elem_opts = [
                            outer_func.add_op(ops.Some(elem_ty), elem) for elem in elems
                        ]
                        return outer_func.add_op(
                            array_new(ht.Option(elem_ty), length), *elem_opts
                        )

                    array_wires: list[Wire] = []
                    wire_idx = 0
                    # First pack bool results into an array.
                    for c_reg in self.input_circuit.c_registers:
                        array_wires.append(
                            pack(
                                wires[wire_idx : wire_idx + c_reg.size],
                                ht.Bool,
                                c_reg.size,
                            )
                        )
                        wire_idx = wire_idx + c_reg.size
                    # Then the borrowed qubits also need to be put back into arrays.
                    for q_reg in self.input_circuit.q_registers:
                        array_wires.append(
                            pack(
                                wires[wire_idx : wire_idx + q_reg.size],
                                ht.Qubit,
                                q_reg.size,
                            )
                        )
                        wire_idx = wire_idx + q_reg.size
                    wires = array_wires

                outer_func.set_outputs(*wires)

        except ImportError:
            pass

        return CompiledPytketDef(
            self.id,
            self.name,
            self.defined_at,
            self.ty,
            self.input_circuit,
            self.use_arrays,
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
        use_arrays: Whether the circuit function uses arrays as input types.
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
        # Use implementation from function definition.
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
        # Use implementation from function definition.
        return compile_call(args, type_args, dfg, self.ty, self.func_def)


def _signature_from_circuit(
    input_circuit: Any,
    globals: Globals,
    defined_at: ToSpan | None,
    use_arrays: bool = False,
) -> FunctionType:
    """Helper function for inferring a function signature from a pytket circuit."""
    try:
        import pytket

        if isinstance(input_circuit, pytket.circuit.Circuit):
            try:
                import tket2  # type: ignore[import-untyped, import-not-found, unused-ignore]  # noqa: F401

                qubit = cast(TypeDef, globals["qubit"]).check_instantiate([], globals)

                if use_arrays:
                    inputs = [
                        FuncInput(array_type(qubit, q_reg.size), InputFlags.Inout)
                        for q_reg in input_circuit.q_registers
                    ]
                    outputs = [
                        array_type(bool_type(), c_reg.size)
                        for c_reg in input_circuit.c_registers
                    ]
                    circuit_signature = FunctionType(
                        inputs,
                        row_to_type(outputs),
                    )
                else:
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
