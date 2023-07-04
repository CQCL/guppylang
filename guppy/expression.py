import ast
from typing import Any, Iterator

from guppy.ast_util import AstVisitor
from guppy.compiler_base import CompilerBase, DFContainer, VarMap
from guppy.error import (
    assert_arith_type,
    assert_bool_type,
    assert_int_type,
    InternalGuppyError,
    GuppyTypeError,
    GuppyError,
)
from guppy.guppy_types import (
    IntType,
    FloatType,
    BoolType,
    FunctionType,
    type_from_python_value,
)
from guppy.hugr.hugr import OutPortV, Hugr


def expr_to_row(expr: ast.expr) -> list[ast.expr]:
    """Turns an expression into a row expressions by unpacking top-level tuples."""
    return expr.elts if isinstance(expr, ast.Tuple) else [expr]


class ExpressionCompiler(CompilerBase, AstVisitor[OutPortV]):
    """A compiler from Python expressions to Hugr."""

    dfg: DFContainer

    def __init__(self, graph: Hugr, global_variables: VarMap):
        self.graph = graph
        self.global_variables = global_variables

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

    def generic_visit(self, node: Any, *args: Any, **kwargs: Any) -> Any:
        raise GuppyError("Expression not supported", node)

    def visit_Constant(self, node: ast.Constant) -> OutPortV:
        if type_from_python_value(node.value) is None:
            raise GuppyError("Unsupported constant expression", node)
        return self.graph.add_constant(node.value).out_port(0)

    def visit_Name(self, node: ast.Name) -> OutPortV:
        x = node.id
        if x in self.dfg or x in self.global_variables:
            var = self.dfg.get_var(x) or self.global_variables[x]
            return var.port
        raise GuppyError(f"Variable `{x}` is not defined", node)

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
        port = self.visit(node.operand)
        ty = port.ty
        if isinstance(node.op, ast.UAdd):
            assert_arith_type(ty, node.operand)
            return port  # Unary plus is a noop
        elif isinstance(node.op, ast.USub):
            assert_arith_type(ty, node.operand)
            func = "ineg" if isinstance(ty, IntType) else "fneg"
            return self.graph.add_arith(func, inputs=[port], out_ty=ty).out_port(0)
        elif isinstance(node.op, ast.Not):
            assert_bool_type(ty, node.operand)
            return self.graph.add_arith("not", inputs=[port], out_ty=ty).out_port(0)
        elif isinstance(node.op, ast.Invert):
            # The unary invert operator `~` is defined as `~x = -(x + 1)` and only valid
            # for integer types.
            # See https://docs.python.org/3/reference/expressions.html#unary-arithmetic-and-bitwise-operations
            # TODO: Do we want to follow the Python definition or have a custom HUGR op?
            assert_int_type(ty, node.operand)
            one = self.graph.add_constant(1)
            inc = self.graph.add_arith(
                "iadd", inputs=[port, one.out_port(0)], out_ty=ty
            )
            inv = self.graph.add_arith("ineg", inputs=[inc.out_port(0)], out_ty=ty)
            return inv.out_port(0)
        else:
            raise InternalGuppyError(
                f"Unexpected unary operator encountered: {node.op}"
            )

    def binary_arith_op(
        self,
        left: OutPortV,
        left_expr: ast.expr,
        right: OutPortV,
        right_expr: ast.expr,
        int_func: str,
        float_func: str,
        bool_out: bool,
    ) -> OutPortV:
        """Helper function for compiling binary arithmetic operations."""
        assert_arith_type(left.ty, left_expr)
        assert_arith_type(right.ty, right_expr)
        # Automatic coercion from `int` to `float` if one of the operands is `float`
        is_float = isinstance(left.ty, FloatType) or isinstance(right.ty, FloatType)
        if is_float:
            if isinstance(left.ty, IntType):
                left = self.graph.add_arith(
                    "int_to_float", inputs=[left], out_ty=FloatType()
                ).out_port(0)
            if isinstance(right.ty, IntType):
                right = self.graph.add_arith(
                    "int_to_float", inputs=[right], out_ty=IntType()
                ).out_port(0)
        return_ty = (
            BoolType() if bool_out else left.ty
        )  # At this point we have `left.ty == right.ty`
        node = self.graph.add_arith(
            float_func if is_float else int_func, inputs=[left, right], out_ty=return_ty
        )
        return node.out_port(0)

    def visit_BinOp(self, node: ast.BinOp) -> OutPortV:
        left = self.visit(node.left)
        right = self.visit(node.right)
        if isinstance(node.op, ast.Add):
            return self.binary_arith_op(
                left, node.left, right, node.right, "iadd", "fadd", False
            )
        elif isinstance(node.op, ast.Sub):
            return self.binary_arith_op(
                left, node.left, right, node.right, "isub", "fsub", False
            )
        elif isinstance(node.op, ast.Mult):
            return self.binary_arith_op(
                left, node.left, right, node.right, "imul", "fmul", False
            )
        elif isinstance(node.op, ast.Div):
            return self.binary_arith_op(
                left, node.left, right, node.right, "idiv", "fdiv", False
            )
        elif isinstance(node.op, ast.Mod):
            return self.binary_arith_op(
                left, node.left, right, node.right, "imod", "fmod", False
            )
        elif isinstance(node.op, ast.Pow):
            return self.binary_arith_op(
                left, node.left, right, node.right, "ipow", "fpow", False
            )
        else:
            raise GuppyError(f"Binary operator `{node.op}` is not supported", node.op)

    def visit_Compare(self, node: ast.Compare) -> OutPortV:
        # Support chained comparisons, e.g. `x <= 5 < y` by compiling to
        # `and(x <= 5, 5 < y)`
        def compile_comparisons() -> Iterator[OutPortV]:
            left_expr = node.left
            left = self.visit(left_expr)
            for right_expr, op in zip(node.comparators, node.ops):
                right = self.visit(right_expr)
                if isinstance(op, ast.Eq) or isinstance(op, ast.Is):
                    # TODO: How is equality defined? What can the operators be?
                    yield self.graph.add_arith(
                        "eq", inputs=[left, right], out_ty=BoolType()
                    ).out_port(0)
                elif isinstance(op, ast.NotEq) or isinstance(op, ast.IsNot):
                    yield self.graph.add_arith(
                        "neq", inputs=[left, right], out_ty=BoolType()
                    ).out_port(0)
                elif isinstance(op, ast.Lt):
                    yield self.binary_arith_op(
                        left, left_expr, right, right_expr, "ilt", "flt", True
                    )
                elif isinstance(op, ast.LtE):
                    yield self.binary_arith_op(
                        left, left_expr, right, right_expr, "ileq", "fleq", True
                    )
                elif isinstance(op, ast.Gt):
                    yield self.binary_arith_op(
                        left, left_expr, right, right_expr, "igt", "fgt", True
                    )
                elif isinstance(op, ast.GtE):
                    yield self.binary_arith_op(
                        left, left_expr, right, right_expr, "igeg", "fgeg", True
                    )
                else:
                    # Remaining cases are `in`, and `not in`.
                    # TODO: We want to support this once collections are added
                    raise GuppyError(
                        f"Binary operator `{ast.unparse(op)}` is not supported", op
                    )
                left = right
                left_expr = right_expr

        acc, *rest = list(compile_comparisons())
        for port in rest:
            acc = self.graph.add_arith(
                "and", inputs=[acc, port], out_ty=BoolType()
            ).out_port(0)
        return acc

    def visit_BoolOp(self, node: ast.BoolOp) -> OutPortV:
        if isinstance(node.op, ast.And):
            func = "and"
        elif isinstance(node.op, ast.Or):
            func = "or"
        else:
            raise InternalGuppyError(f"Unexpected BoolOp encountered: {node.op}")
        operands = [self.visit(operand) for operand in node.values]
        acc = operands[0]
        for operand in operands[1:]:
            acc = self.graph.add_arith(
                func, inputs=[acc, operand], out_ty=BoolType()
            ).out_port(0)
        return acc

    def visit_Call(self, node: ast.Call) -> OutPortV:
        # We need to figure out if this is a direct or indirect call
        f = node.func
        if (
            isinstance(f, ast.Name)
            and f.id in self.global_variables
            and f.id not in self.dfg
        ):
            is_direct = True
            var = self.global_variables[f.id]
            func_port = var.port
        else:
            is_direct = False
            func_port = self.visit(f)

        func_ty = func_port.ty
        if not isinstance(func_ty, FunctionType):
            raise GuppyTypeError(f"Expected function type, got `{func_ty}`", f)
        if len(node.keywords) > 0:
            # TODO: Implement this
            raise GuppyError(
                f"Argument passing by keyword is not supported", node.keywords[0]
            )
        exp, act = len(func_ty.args), len(node.args)
        if act < exp:
            raise GuppyTypeError(
                f"Not enough arguments passed (expected {exp}, got {act})", node
            )
        if exp < act:
            raise GuppyTypeError(f"Unexpected argument", node.args[exp])

        args = [self.visit(arg) for arg in node.args]
        for i, port in enumerate(args):
            if port.ty != func_ty.args[i]:
                raise GuppyTypeError(
                    f"Expected argument of type `{func_ty.args[i]}`, got `{port.ty}`",
                    node.args[i],
                )

        if is_direct:
            call = self.graph.add_call(func_port, args)
        else:
            call = self.graph.add_indirect_call(func_port, args)

        # Group outputs into tuple
        returns = [call.out_port(i) for i in range(len(func_ty.returns))]
        if len(returns) != 1:
            return self.graph.add_make_tuple(inputs=returns).out_port(0)
        return returns[0]
