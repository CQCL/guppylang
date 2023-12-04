import ast
from typing import Any

from guppy.ast_util import AstVisitor, get_type
from guppy.compiler.core import CompiledFunction, CompilerBase, DFContainer
from guppy.error import InternalGuppyError
from guppy.gtypes import BoolType, FunctionType, type_to_row
from guppy.hugr import ops, val
from guppy.hugr.hugr import OutPortV
from guppy.nodes import GlobalCall, GlobalName, LocalCall, LocalName


class ExprCompiler(CompilerBase, AstVisitor[OutPortV]):
    """A compiler from Guppy expressions to Hugr."""

    dfg: DFContainer

    def compile(self, expr: ast.expr, dfg: DFContainer) -> OutPortV:
        """Compiles an expression and returns a single port holding the output value."""
        self.dfg = dfg
        with self.graph.parent(dfg.node):
            res = self.visit(expr)
        return res

    def compile_row(self, expr: ast.expr, dfg: DFContainer) -> list[OutPortV]:
        """Compiles a row expression and returns a list of ports, one for each value in
        the row.

        On Python-level, we treat tuples like rows on top-level. However, nested tuples
        are treated like regular Guppy tuples.
        """
        return [self.compile(e, dfg) for e in expr_to_row(expr)]

    def visit_Constant(self, node: ast.Constant) -> OutPortV:
        if value := python_value_to_hugr(node.value):
            const = self.graph.add_constant(value, get_type(node)).out_port(0)
            return self.graph.add_load_constant(const).out_port(0)
        msg = "Unsupported constant expression in compiler"
        raise InternalGuppyError(msg)

    def visit_LocalName(self, node: LocalName) -> OutPortV:
        return self.dfg[node.id].port

    def visit_GlobalName(self, node: GlobalName) -> OutPortV:
        return self.globals[node.id].load(self.dfg, self.graph, self.globals, node)

    def visit_Name(self, node: ast.Name) -> OutPortV:
        msg = "Node should have been removed during type checking."
        raise InternalGuppyError(msg)

    def visit_Tuple(self, node: ast.Tuple) -> OutPortV:
        return self.graph.add_make_tuple(
            inputs=[self.visit(e) for e in node.elts]
        ).out_port(0)

    def _pack_returns(self, returns: list[OutPortV]) -> OutPortV:
        """Groups function return values into a tuple"""
        if len(returns) != 1:
            return self.graph.add_make_tuple(inputs=returns).out_port(0)
        return returns[0]

    def visit_LocalCall(self, node: LocalCall) -> OutPortV:
        func = self.visit(node.func)
        assert isinstance(func.ty, FunctionType)

        args = [self.visit(arg) for arg in node.args]
        call = self.graph.add_indirect_call(func, args)
        rets = [call.out_port(i) for i in range(len(type_to_row(func.ty.returns)))]
        return self._pack_returns(rets)

    def visit_GlobalCall(self, node: GlobalCall) -> OutPortV:
        func = self.globals[node.func.name]
        assert isinstance(func, CompiledFunction)

        args = [self.visit(arg) for arg in node.args]
        rets = func.compile_call(args, self.dfg, self.graph, self.globals, node)
        return self._pack_returns(rets)

    def visit_Call(self, node: ast.Call) -> OutPortV:
        msg = "Node should have been removed during type checking."
        raise InternalGuppyError(msg)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> OutPortV:
        # The only case that is not desugared by the type checker is the `not` operation
        # since it is not implemented via a dunder method
        if isinstance(node.op, ast.Not):
            arg = self.visit(node.operand)
            return self.graph.add_node(
                ops.CustomOp(extension="logic", op_name="Not", args=[]), inputs=[arg]
            ).add_out_port(BoolType())

        msg = "Node should have been removed during type checking."
        raise InternalGuppyError(msg)

    def visit_BinOp(self, node: ast.BinOp) -> OutPortV:
        msg = "Node should have been removed during type checking."
        raise InternalGuppyError(msg)

    def visit_Compare(self, node: ast.Compare) -> OutPortV:
        msg = "Node should have been removed during type checking."
        raise InternalGuppyError(msg)


def expr_to_row(expr: ast.expr) -> list[ast.expr]:
    """Turns an expression into a row expressions by unpacking top-level tuples."""
    return expr.elts if isinstance(expr, ast.Tuple) else [expr]


def python_value_to_hugr(v: Any) -> val.Value | None:
    """Turns a Python value into a Hugr value.

    Returns None if the Python value cannot be represented in Guppy.
    """
    from guppy.prelude._internal import bool_value, float_value, int_value

    if isinstance(v, bool):
        return bool_value(v)
    elif isinstance(v, int):
        return int_value(v)
    elif isinstance(v, float):
        return float_value(v)
    return None
