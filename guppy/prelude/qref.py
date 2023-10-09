"""Prototype for qubit references."""

# mypy: disable-error-code=empty-body

import ast

from typing import Optional

from guppy.cfg.builder import is_tmp_var
from guppy.compiler_base import Variable, CallCompiler, DFContainer
from guppy.error import GuppyError
from guppy.expression import type_check_call
from guppy.guppy_types import TupleType, GuppyType, ArrayType, SumType
from guppy.hugr.hugr import OutPortV, Node, Hugr
from guppy.prelude import builtin, quantum
from guppy.extension import GuppyExtension, ExtensionFunction
from guppy.hugr import ops
from guppy.prelude.builtin import IntType
from guppy.prelude.quantum import Qubit


MEMORY_VAR = "%mem"


class MemoryType(ArrayType):
    def __init__(self) -> None:
        # TODO: length??
        super().__init__(SumType([Qubit(), TupleType([])]), len=42)  # type: ignore

    def __str__(self) -> str:
        return "Mem"

    @property
    def linear(self) -> bool:
        # TODO: Pretend memory is not linear until we have usage tracking of %mem
        return False


# TODO: It would be better if this lazy ref stuff would live in the Variable, but how to
#  deal with reassignment of variables (i.e. q2 = q1) ???


class LazyRefPort(OutPortV):
    """Port for a linear value that can be treated like reference, but is not yet turned
    into one.

    When creating a reference via `r = ref(q)`, we don't put the qubit into memory
    immediately. Instead, we mark it as a lazy ref using this class and only create the
    actual reference once the members of the port are accessed. This way, we can do
    `deref(r)` for free as long as the reference has not been materialised yet (by
    returning the original port).
    """

    qubit_port: Optional[OutPortV]
    ref_port: Optional[OutPortV]
    dfg: DFContainer
    graph: Hugr

    in_use: bool

    def __init__(
        self,
        original_port: OutPortV,
        dfg: DFContainer,
        graph: Hugr,
        ref_port: Optional[OutPortV] = None,
    ) -> None:
        self.qubit_port = original_port
        self.dfg = dfg
        self.graph = graph
        self.in_use = False
        self.ref_port = ref_port

    def get_ref_port(self) -> OutPortV:
        if self.ref_port is None:
            mem = self.dfg[MEMORY_VAR].port
            app = self.graph.add_node(
                ops.DummyOp(name="append"),
                inputs=[mem, self.qubit_port],  # type: ignore
                parent=self.dfg.node,
            )
            mem, ref = app.add_out_port(MemoryType()), app.add_out_port(QRef())  # type: ignore
            self.dfg[MEMORY_VAR].port = mem
            self.ref_port = ref
            self.qubit_port = None
        elif self.qubit_port is not None:
            mem = self.dfg[MEMORY_VAR].port
            put = self.graph.add_node(
                ops.DummyOp(name="put"),
                inputs=[mem, self.ref_port, self.get_qubit_port()],
                parent=self.dfg.node,
            )
            self.dfg[MEMORY_VAR].port = put.add_out_port(MemoryType())
            self.qubit_port = None
        return self.ref_port

    def get_qubit_port(self) -> OutPortV:
        if self.qubit_port is None:
            assert self.ref_port is not None
            mem = self.dfg[MEMORY_VAR].port
            get = self.graph.add_node(
                ops.DummyOp(name="get"),
                inputs=[mem, self.ref_port],
                parent=self.dfg.node,
            )
            mem, qubit = get.add_out_port(MemoryType()), get.add_out_port(Qubit())  # type: ignore
            self.dfg[MEMORY_VAR].port = mem
            self.qubit_port = qubit
        return self.qubit_port

    @property
    def ty(self) -> GuppyType:
        return QRef()  # type: ignore

    @property
    def node(self) -> Node:
        return self.get_ref_port().node

    @property
    def offset(self) -> int:
        return self.get_ref_port().offset


class MakeRefCompiler(CallCompiler):
    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        type_check_call(self.func.ty, args, self.node)
        [arg] = args
        return [LazyRefPort(arg, self.dfg, self.graph)]


class DerefCompiler(CallCompiler):
    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        type_check_call(self.func.ty, args, self.node)
        [arg] = args
        if isinstance(arg, LazyRefPort):
            if arg.in_use:
                raise GuppyError(
                    "Qubit reference cannot be dereferenced since it is already in use",
                    self.node,
                )
            arg.in_use = True
            return [arg.get_qubit_port()]
        mem = self.dfg[MEMORY_VAR].port
        get = self.graph.add_node(ops.DummyOp(name="get"), inputs=[mem, arg])
        mem, qubit = get.add_out_port(MemoryType()), get.add_out_port(Qubit())  # type: ignore
        self.dfg[MEMORY_VAR].port = mem
        return [qubit]


class UpdaterefCompiler(CallCompiler):
    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        type_check_call(self.func.ty, args, self.node)
        [ref_port, qubit_port] = args
        if isinstance(ref_port, LazyRefPort):
            if not ref_port.in_use:
                raise GuppyError(
                    "The reference cannot be updated since it contains an unused qubit",
                    self.node,
                )
            ref_port.qubit_port = qubit_port
            ref_port.in_use = False
        else:
            if isinstance(self.node, ast.Call):
                ref_node = self.node.args[0]
                if isinstance(ref_node, ast.Name) and not is_tmp_var(ref_node.id):
                    self.dfg[ref_node.id].port = LazyRefPort(
                        qubit_port, self.dfg, self.graph, ref_port
                    )
                    return []
            mem = self.dfg[MEMORY_VAR].port
            put = self.graph.add_node(
                ops.DummyOp(name="put"), inputs=[mem, ref_port, qubit_port]
            )
            self.dfg[MEMORY_VAR].port = put.add_out_port(MemoryType())
        return []


class RefOpCompiler(CallCompiler):
    original_func: ExtensionFunction

    def __init__(self, original_func: ExtensionFunction):
        self.original_func = original_func

    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        type_check_call(self.func.ty, args, self.node)
        qubit_args = [
            deref.compile_call([arg], self.dfg, self.graph, self.globals, self.node)[0]
            for arg in args
        ]
        rets = self.original_func.compile_call(
            qubit_args, self.dfg, self.graph, self.globals, self.node
        )
        arg_nodes = (
            self.node.args if isinstance(self.node, ast.Call) else [None] * len(args)  # type: ignore
        )
        for arg, ret, arg_node in zip(args, rets, arg_nodes):
            node = ast.Call(func=None, args=[arg_node]) if arg_node else self.node
            updateref.compile_call([arg, ret], self.dfg, self.graph, self.globals, node)
        return []  # [LazyRefPort(ret, self.dfg, self.graph) for ret in rets]


class InitMemCompiler(CallCompiler):
    def compile(self, args: list[OutPortV]) -> list[OutPortV]:
        type_check_call(self.func.ty, args, self.node)
        mem = self.graph.add_node(ops.DummyOp(name="new")).add_out_port(MemoryType())
        self.dfg[MEMORY_VAR] = Variable(MEMORY_VAR, mem, self.node)
        return []


extension = GuppyExtension("qref", dependencies=[builtin, quantum])


@extension.type(IntType().to_hugr())
class QRef:
    pass


@extension.func(MakeRefCompiler())
def ref(q: Qubit) -> QRef:
    ...


@extension.func(DerefCompiler())
def deref(r: QRef) -> Qubit:
    ...


@extension.func(UpdaterefCompiler())
def updateref(r: QRef, q: Qubit) -> None:
    ...


@extension.func(InitMemCompiler())
def initmem() -> None:
    ...


@extension.func(RefOpCompiler(quantum.h))
def h(q: QRef) -> None:
    ...


@extension.func(RefOpCompiler(quantum.cx))
def cx(control: QRef, target: QRef) -> None:
    ...
