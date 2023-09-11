import ast
from typing import Any, Optional

from guppy.ast_util import AstVisitor, AstNode
from guppy.compiler_base import (
    CompilerBase,
    DFContainer,
    GlobalFunction,
    GlobalVariable,
)
from guppy.error import InternalGuppyError, GuppyTypeError, GuppyError
from guppy.guppy_types import FunctionType
from guppy.hugr.hugr import OutPortV

# Mapping from unary AST op to dunder method and display name
unary_table: dict[type[AstNode], tuple[str, str]] = {
    ast.UAdd: ("__pos__", "+"),
    ast.USub: ("__neg__", "-"),
    ast.Invert: ("__invert__", "~"),
}

# Mapping from binary AST op to left dunder method, right dunder method and display name
binary_table: dict[type[AstNode], tuple[str, str, str]] = {
    ast.Add: ("__add__", "__radd__", "+"),
    ast.Sub: ("__sub__", "__rsub__", "-"),
    ast.Mult: ("__mul__", "__rmul__", "*"),
    ast.Div: ("__truediv__", "__rtruediv__", "/"),
    ast.FloorDiv: ("__floordiv__", "__rfloordiv__", "//"),
    ast.Mod: ("__mod__", "__rmod__", "%"),
    ast.Pow: ("__pow__", "__rpow__", "**"),
    ast.LShift: ("__lshift__", "__rlshift__", "<<"),
    ast.RShift: ("__rshift__", "__rrshift__", ">>"),
    ast.BitOr: ("__or__", "__ror__", "||"),
    ast.BitXor: ("__xor__", "__rxor__", "^"),
    ast.BitAnd: ("__and__", "__rand__", "&&"),
    ast.MatMult: ("__matmul__", "__rmatmul__", "@"),
    ast.Eq: ("__eq__", "__eq__", "=="),
    ast.NotEq: ("__neq__", "__neq__", "!="),
    ast.Lt: ("__lt__", "__gt__", "<"),
    ast.LtE: ("__le__", "__ge__", "<="),
    ast.Gt: ("__gt__", "__lt__", ">"),
    ast.GtE: ("__ge__", "__le__", ">="),
}


def expr_to_row(expr: ast.expr) -> list[ast.expr]:
    """Turns an expression into a row expressions by unpacking top-level tuples."""
    return expr.elts if isinstance(expr, ast.Tuple) else [expr]


class ExpressionCompiler(CompilerBase, AstVisitor[OutPortV]):
    """A compiler from Python expressions to Hugr."""

    dfg: DFContainer

    def compile(self, expr: ast.expr, dfg: DFContainer) -> OutPortV:
        """Compiles an expression and returns a single port holding the output value."""
        self.dfg = dfg
        with self.graph.parent(dfg.node):
            res = self.visit(expr)
        return res

    def compile_row(self, expr: ast.expr, dfg: DFContainer) -> list[OutPortV]:
        """Compiles a row expression and returns a list of ports, one for
        each value in the row.

        On Python-level, we treat tuples like rows on top-level. However,
        nested tuples are treated like regular Guppy tuples.
        """
        return [self.compile(e, dfg) for e in expr_to_row(expr)]

    def _is_global_var(self, x: str) -> Optional[GlobalVariable]:
        """Returns `True` if the argument references a global variable."""
        if x in self.globals.values and x not in self.dfg:
            return self.globals.values[x]
        return None

    def generic_visit(self, node: Any, *args: Any, **kwargs: Any) -> Any:
        raise GuppyError("Expression not supported", node)

    def visit_Constant(self, node: ast.Constant) -> OutPortV:
        from guppy.prelude.builtin import (
            IntType,
            BoolType,
            FloatType,
            int_value,
            bool_value,
            float_value,
        )

        v = node.value
        if isinstance(v, bool):
            const = self.graph.add_constant(bool_value(v), BoolType()).out_port(0)
        elif isinstance(v, int):
            const = self.graph.add_constant(int_value(v), IntType()).out_port(0)
        elif isinstance(v, float):
            const = self.graph.add_constant(float_value(v), FloatType()).out_port(0)
        else:
            raise GuppyError("Unsupported constant expression", node)
        return self.graph.add_load_constant(const).out_port(0)

    def visit_Name(self, node: ast.Name) -> OutPortV:
        x = node.id
        if x in self.dfg:
            var = self.dfg[x]
            if var.ty.linear and var.used is not None:
                raise GuppyError(
                    f"Variable `{x}` with linear type `{var.ty}` was "
                    "already used (at {0})",
                    node,
                    [var.used],
                )
            var.used = node
            return self.dfg[x].port
        elif x in self.globals.values:
            return self.globals.values[x].load(
                self.graph, self.dfg.node, self.globals, node
            )
        raise InternalGuppyError(
            f"Variable `{x}` is not defined in ExpressionCompiler. This should have "
            f"been caught by program analysis!"
        )

    def visit_JoinedString(self, node: ast.JoinedStr) -> OutPortV:
        raise GuppyError("Guppy does not support formatted strings", node)

    def visit_Tuple(self, node: ast.Tuple) -> OutPortV:
        return self.graph.add_make_tuple(
            inputs=[self.visit(e) for e in node.elts]
        ).out_port(0)

    def visit_List(self, node: ast.List) -> OutPortV:
        raise NotImplementedError()

    def visit_Set(self, node: ast.Set) -> OutPortV:
        raise NotImplementedError()

    def visit_Dict(self, node: ast.Dict) -> OutPortV:
        raise NotImplementedError()

    def visit_UnaryOp(self, node: ast.UnaryOp) -> OutPortV:
        if isinstance(node.op, ast.Not):
            raise InternalGuppyError(
                "BB contains unary `Not` op. Should have been removed during CFG "
                f"construction: `{ast.unparse(node)}`"
            )

        # Compile by calling out to instance dunder methods
        arg = self.visit(node.operand)
        op, display_name = unary_table[node.op.__class__]
        func = self.globals.get_instance_func(arg.ty, op)
        if func is None:
            raise GuppyTypeError(
                f"Unary operator `{display_name}` not defined for argument of type "
                f" `{arg.ty}`",
                node.operand,
            )
        [res] = func.compile_call([arg], self.dfg.node, self.graph, self.globals, node)
        return res

    def _compile_binary(
        self, left_expr: AstNode, right_expr: AstNode, op: AstNode, node: AstNode
    ) -> OutPortV:
        """Helper method to compile binary operators by calling out to dunder methods.

        For example, first try calling `__add__` on the left operand. If that fails, try
        `__radd__` on the right operand.
        """
        if op.__class__ not in binary_table:
            raise GuppyError("This binary operation is not supported by Guppy.")
        lop, rop, display_name = binary_table[op.__class__]
        left, right = self.visit(left_expr), self.visit(right_expr)

        if func := self.globals.get_instance_func(left.ty, lop):
            try:
                [ret] = func.compile_call(
                    [left, right], self.dfg.node, self.graph, self.globals, node
                )
                return ret
            except GuppyError:
                pass

        if func := self.globals.get_instance_func(right.ty, lop):
            try:
                [ret] = func.compile_call(
                    [left, right], self.dfg.node, self.graph, self.globals, node
                )
                return ret
            except GuppyError:
                pass

        raise GuppyTypeError(
            f"Binary operator `{display_name}` not defined for arguments of type "
            f"`{left.ty}` and `{right.ty}`",
            node,
        )

    def visit_BinOp(self, node: ast.BinOp) -> OutPortV:
        return self._compile_binary(node.left, node.right, node.op, node)

    def visit_Compare(self, node: ast.Compare) -> OutPortV:
        if len(node.comparators) != 1 or len(node.ops) != 1:
            raise InternalGuppyError(
                "BB contains chained comparison. Should have been removed during CFG "
                "construction."
            )
        left_expr, [op], [right_expr] = node.left, node.ops, node.comparators
        return self._compile_binary(left_expr, right_expr, op, node)

    def visit_Call(self, node: ast.Call) -> OutPortV:
        func = node.func
        if len(node.keywords) > 0:
            raise GuppyError(
                f"Argument passing by keyword is not supported", node.keywords[0]
            )

        # Special case for calls of global module-level functions. This also handles
        # calls of extension functions.
        if (
            isinstance(func, ast.Name)
            and (f := self._is_global_var(func.id))
            and isinstance(f, GlobalFunction)
        ):
            args = [self.visit(arg) for arg in node.args]
            returns = f.compile_call(
                args, self.dfg.node, self.graph, self.globals, node
            )

        # Otherwise, compile the function like any other expression
        else:
            func_port = self.visit(func)
            func_ty = func_port.ty
            if not isinstance(func_ty, FunctionType):
                raise GuppyTypeError(f"Expected function type, got `{func_ty}`", func)

            args = [self.visit(arg) for arg in node.args]
            type_check_call(func_ty, args, node)
            call = self.graph.add_indirect_call(func_port, args)
            returns = [call.out_port(i) for i in range(len(func_ty.returns))]

        # Group outputs into tuple
        if len(returns) != 1:
            return self.graph.add_make_tuple(inputs=returns).out_port(0)
        return returns[0]

    def visit_NamedExpr(self, node: ast.NamedExpr) -> OutPortV:
        raise InternalGuppyError(
            "BB contains `NamedExpr`. Should have been removed during CFG"
            f"construction: `{ast.unparse(node)}`"
        )

    def visit_BoolOp(self, node: ast.BoolOp) -> OutPortV:
        raise InternalGuppyError(
            "BB contains `BoolOp`. Should have been removed during CFG construction: "
            f"`{ast.unparse(node)}`"
        )

    def visit_IfExp(self, node: ast.IfExp) -> OutPortV:
        raise InternalGuppyError(
            "BB contains `IfExp`. Should have been removed during CFG construction: "
            f"`{ast.unparse(node)}`"
        )


def check_num_args(exp: int, act: int, node: AstNode) -> None:
    """Checks that the correct number of arguments have been passed to a function."""
    if act < exp:
        raise GuppyTypeError(
            f"Not enough arguments passed (expected {exp}, got {act})", node
        )
    if exp < act:
        if isinstance(node, ast.Call):
            raise GuppyTypeError(f"Unexpected argument", node.args[exp])
        raise GuppyTypeError(
            f"Too many arguments passed (expected {exp}, got {act})", node
        )


def type_check_call(func_ty: FunctionType, args: list[OutPortV], node: AstNode) -> None:
    """Type-checks the arguments for a function call."""
    check_num_args(len(func_ty.args), len(args), node)
    for i, port in enumerate(args):
        if port.ty != func_ty.args[i]:
            raise GuppyTypeError(
                f"Expected argument of type `{func_ty.args[i]}`, got `{port.ty}`",
                node.args[i] if isinstance(node, ast.Call) else node,
            )
