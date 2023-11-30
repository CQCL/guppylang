"""Type checking and synthesizing code for expressions.

Operates on expressions in a basic block after CFG construction. In particular, we
assume that expressions that involve control flow (i.e. short-circuiting and ternary
expressions) have been removed during CFG construction.

Furthermore, we assume that assignment expressions with the walrus operator := have
been turned into regular assignments and are no longer present. As a result, expressions
are assumed to be side effect free, in the sense that they do not modify the variables
available in the type checking context.

We may alter/desugar AST nodes during type checking. In particular, we turn `ast.Name`
nodes into either `LocalName` or `GlobalName` nodes and `ast.Call` nodes are turned into
`LocalCall` or `GlobalCall` nodes. Furthermore, all nodes in the resulting AST are
annotated with their type.

Expressions can be checked against a given type by the `ExprChecker`, raising an Error
if the expressions doesn't have the expected type. Checking is used for annotated
assignments, return values, and function arguments. Alternatively, the `ExprSynthesizer`
can be used to infer a type for an expression.
"""

import ast
from typing import Optional, Union, NoReturn, Any

from guppy.ast_util import AstVisitor, with_loc, AstNode, with_type, get_type_opt
from guppy.checker.core import Context, CallableVariable, Globals
from guppy.error import GuppyError, GuppyTypeError, InternalGuppyError
from guppy.gtypes import GuppyType, TupleType, FunctionType, BoolType
from guppy.nodes import LocalName, GlobalName, LocalCall

# Mapping from unary AST op to dunder method and display name
unary_table: dict[type[ast.unaryop], tuple[str, str]] = {
    ast.UAdd: ("__pos__", "+"),
    ast.USub: ("__neg__", "-"),
    ast.Invert: ("__invert__", "~"),
}

# Mapping from binary AST op to left dunder method, right dunder method and display name
AstOp = Union[ast.operator, ast.cmpop]
binary_table: dict[type[AstOp], tuple[str, str, str]] = {
    ast.Add: ("__add__", "__radd__", "+"),
    ast.Sub: ("__sub__", "__rsub__", "-"),
    ast.Mult: ("__mul__", "__rmul__", "*"),
    ast.Div: ("__truediv__", "__rtruediv__", "/"),
    ast.FloorDiv: ("__floordiv__", "__rfloordiv__", "//"),
    ast.Mod: ("__mod__", "__rmod__", "%"),
    ast.Pow: ("__pow__", "__rpow__", "**"),
    ast.LShift: ("__lshift__", "__rlshift__", "<<"),
    ast.RShift: ("__rshift__", "__rrshift__", ">>"),
    ast.BitOr: ("__or__", "__ror__", "|"),
    ast.BitXor: ("__xor__", "__rxor__", "^"),
    ast.BitAnd: ("__and__", "__rand__", "&"),
    ast.MatMult: ("__matmul__", "__rmatmul__", "@"),
    ast.Eq: ("__eq__", "__eq__", "=="),
    ast.NotEq: ("__neq__", "__neq__", "!="),
    ast.Lt: ("__lt__", "__gt__", "<"),
    ast.LtE: ("__le__", "__ge__", "<="),
    ast.Gt: ("__gt__", "__lt__", ">"),
    ast.GtE: ("__ge__", "__le__", ">="),
}


class ExprChecker(AstVisitor[ast.expr]):
    """Checks an expression against a type and produces a new type-annotated AST"""

    ctx: Context

    # Name for the kind of term we are currently checking against (used in errors).
    # For example, "argument", "return value", or in general "expression".
    _kind: str

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx
        self._kind = "expression"

    def _fail(
        self,
        expected: GuppyType,
        actual: Union[ast.expr, GuppyType],
        loc: Optional[AstNode] = None,
    ) -> NoReturn:
        """Raises a type error indicating that the type doesn't match."""
        if not isinstance(actual, GuppyType):
            loc = loc or actual
            _, actual = self._synthesize(actual)
        assert loc is not None
        raise GuppyTypeError(
            f"Expected {self._kind} of type `{expected}`, got `{actual}`", loc
        )

    def check(
        self, expr: ast.expr, ty: GuppyType, kind: str = "expression"
    ) -> ast.expr:
        """Checks an expression against a type.

        Returns a new desugared expression with type annotations.
        """
        old_kind = self._kind
        self._kind = kind or self._kind
        expr = self.visit(expr, ty)
        self._kind = old_kind
        return with_type(ty, expr)

    def _synthesize(self, node: ast.expr) -> tuple[ast.expr, GuppyType]:
        """Invokes the type synthesiser"""
        return ExprSynthesizer(self.ctx).synthesize(node)

    def visit_Tuple(self, node: ast.Tuple, ty: GuppyType) -> ast.expr:
        if not isinstance(ty, TupleType) or len(ty.element_types) != len(node.elts):
            return self._fail(ty, node)
        for i, el in enumerate(node.elts):
            node.elts[i] = self.check(el, ty.element_types[i])
        return node

    def generic_visit(self, node: ast.expr, ty: GuppyType) -> ast.expr:  # type: ignore
        # Try to synthesize and then check if it matches the given type
        node, synth = self._synthesize(node)
        if synth != ty:
            self._fail(ty, synth, node)
        return node


class ExprSynthesizer(AstVisitor[tuple[ast.expr, GuppyType]]):
    ctx: Context

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx

    def synthesize(self, node: ast.expr) -> tuple[ast.expr, GuppyType]:
        """Tries to synthesise a type for the given expression.

        Also returns a new desugared expression with type annotations.
        """
        if ty := get_type_opt(node):
            return node, ty
        node, ty = self.visit(node)
        return with_type(ty, node), ty

    def _check(
        self, expr: ast.expr, ty: GuppyType, kind: str = "expression"
    ) -> ast.expr:
        """Checks an expression against a given type"""
        return ExprChecker(self.ctx).check(expr, ty, kind)

    def visit_Constant(self, node: ast.Constant) -> tuple[ast.expr, GuppyType]:
        ty = python_value_to_guppy_type(node.value, node, self.ctx.globals)
        if ty is None:
            raise GuppyError("Unsupported constant", node)
        return node, ty

    def visit_Name(self, node: ast.Name) -> tuple[ast.expr, GuppyType]:
        x = node.id
        if x in self.ctx.locals:
            var = self.ctx.locals[x]
            if var.ty.linear and var.used is not None:
                raise GuppyError(
                    f"Variable `{x}` with linear type `{var.ty}` was "
                    "already used (at {0})",
                    node,
                    [var.used],
                )
            var.used = node
            return with_loc(node, LocalName(id=x)), var.ty
        elif x in self.ctx.globals.values:
            # Cache value in the AST
            value = self.ctx.globals.values[x]
            return with_loc(node, GlobalName(id=x, value=value)), value.ty
        raise InternalGuppyError(
            f"Variable `{x}` is not defined in `TypeSynthesiser`. This should have "
            f"been caught by program analysis!"
        )

    def visit_Tuple(self, node: ast.Tuple) -> tuple[ast.expr, GuppyType]:
        elems = [self.synthesize(elem) for elem in node.elts]
        node.elts = [n for n, _ in elems]
        return node, TupleType([ty for _, ty in elems])

    def visit_UnaryOp(self, node: ast.UnaryOp) -> tuple[ast.expr, GuppyType]:
        # We need to synthesise the argument type, so we can look up dunder methods
        node.operand, op_ty = self.synthesize(node.operand)

        # Special case for the `not` operation since it is not implemented via a dunder
        # method or control-flow
        if isinstance(node.op, ast.Not):
            node.operand, bool_ty = to_bool(node.operand, op_ty, self.ctx)
            return node, bool_ty

        # Check all other unary expressions by calling out to instance dunder methods
        op, display_name = unary_table[node.op.__class__]
        func = self.ctx.globals.get_instance_func(op_ty, op)
        if func is None:
            raise GuppyTypeError(
                f"Unary operator `{display_name}` not defined for argument of type "
                f" `{op_ty}`",
                node.operand,
            )
        return func.synthesize_call([node.operand], node, self.ctx)

    def _synthesize_binary(
        self, left_expr: ast.expr, right_expr: ast.expr, op: AstOp, node: ast.expr
    ) -> tuple[ast.expr, GuppyType]:
        """Helper method to compile binary operators by calling out to dunder methods.

        For example, first try calling `__add__` on the left operand. If that fails, try
        `__radd__` on the right operand.
        """
        if op.__class__ not in binary_table:
            raise GuppyError("This binary operation is not supported by Guppy.", op)
        lop, rop, display_name = binary_table[op.__class__]
        left_expr, left_ty = self.synthesize(left_expr)
        right_expr, right_ty = self.synthesize(right_expr)

        if func := self.ctx.globals.get_instance_func(left_ty, lop):
            try:
                return func.synthesize_call([left_expr, right_expr], node, self.ctx)
            except GuppyError:
                pass

        if func := self.ctx.globals.get_instance_func(right_ty, rop):
            try:
                return func.synthesize_call([right_expr, left_expr], node, self.ctx)
            except GuppyError:
                pass

        raise GuppyTypeError(
            f"Binary operator `{display_name}` not defined for arguments of type "
            f"`{left_ty}` and `{right_ty}`",
            node,
        )

    def visit_BinOp(self, node: ast.BinOp) -> tuple[ast.expr, GuppyType]:
        return self._synthesize_binary(node.left, node.right, node.op, node)

    def visit_Compare(self, node: ast.Compare) -> tuple[ast.expr, GuppyType]:
        if len(node.comparators) != 1 or len(node.ops) != 1:
            raise InternalGuppyError(
                "BB contains chained comparison. Should have been removed during CFG "
                "construction."
            )
        left_expr, [op], [right_expr] = node.left, node.ops, node.comparators
        return self._synthesize_binary(left_expr, right_expr, op, node)

    def visit_Call(self, node: ast.Call) -> tuple[ast.expr, GuppyType]:
        if len(node.keywords) > 0:
            raise GuppyError(
                "Argument passing by keyword is not supported", node.keywords[0]
            )
        node.func, ty = self.synthesize(node.func)

        # First handle direct calls of user-defined functions and extension functions
        if isinstance(node.func, GlobalName) and isinstance(
            node.func.value, CallableVariable
        ):
            return node.func.value.synthesize_call(node.args, node, self.ctx)

        # Otherwise, it must be a function as a higher-order value
        if isinstance(ty, FunctionType):
            args, return_ty = synthesize_call(ty, node.args, node, self.ctx)
            return with_loc(node, LocalCall(func=node.func, args=args)), return_ty
        elif f := self.ctx.globals.get_instance_func(ty, "__call__"):
            return f.synthesize_call(node.args, node, self.ctx)
        else:
            raise GuppyTypeError(f"Expected function type, got `{ty}`", node.func)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> tuple[ast.expr, GuppyType]:
        raise InternalGuppyError(
            "BB contains `NamedExpr`. Should have been removed during CFG"
            f"construction: `{ast.unparse(node)}`"
        )

    def visit_BoolOp(self, node: ast.BoolOp) -> tuple[ast.expr, GuppyType]:
        raise InternalGuppyError(
            "BB contains `BoolOp`. Should have been removed during CFG construction: "
            f"`{ast.unparse(node)}`"
        )

    def visit_IfExp(self, node: ast.IfExp) -> tuple[ast.expr, GuppyType]:
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
            raise GuppyTypeError("Unexpected argument", node.args[exp])
        raise GuppyTypeError(
            f"Too many arguments passed (expected {exp}, got {act})", node
        )


def synthesize_call(
    func_ty: FunctionType, args: list[ast.expr], node: AstNode, ctx: Context
) -> tuple[list[ast.expr], GuppyType]:
    """Synthesizes the return type of a function call.

    Also returns desugared versions of the arguments with type annotations.
    """
    check_num_args(len(func_ty.args), len(args), node)
    for i, arg in enumerate(args):
        args[i] = ExprChecker(ctx).check(arg, func_ty.args[i], "argument")
    return args, func_ty.returns


def check_call(
    func_ty: FunctionType,
    args: list[ast.expr],
    ty: GuppyType,
    node: AstNode,
    ctx: Context,
) -> list[ast.expr]:
    """Checks the return type of a function call against a given type"""
    args, return_ty = synthesize_call(func_ty, args, node, ctx)
    if return_ty != ty:
        raise GuppyTypeError(
            f"Expected expression of type `{ty}`, got `{return_ty}`", node
        )
    return args


def to_bool(
    node: ast.expr, node_ty: GuppyType, ctx: Context
) -> tuple[ast.expr, GuppyType]:
    """Tries to turn a node into a bool"""
    if isinstance(node_ty, BoolType):
        return node, node_ty

    func = ctx.globals.get_instance_func(node_ty, "__bool__")
    if func is None:
        raise GuppyTypeError(
            f"Expression of type `{node_ty}` cannot be interpreted as a `bool`",
            node,
        )

    # We could check the return type against bool, but we can give a better error
    # message if we synthesise and compare to bool by hand
    call, return_ty = func.synthesize_call([node], node, ctx)
    if not isinstance(return_ty, BoolType):
        raise GuppyTypeError(
            f"`__bool__` on type `{node_ty}` returns `{return_ty}` instead of `bool`",
            node,
        )
    return call, return_ty


def python_value_to_guppy_type(
    v: Any, node: ast.expr, globals: Globals
) -> Optional[GuppyType]:
    """Turns a primitive Python value into a Guppy type.

    Returns `None` if the Python value cannot be represented in Guppy.
    """
    if isinstance(v, bool):
        return globals.types["bool"].build(node=node)
    elif isinstance(v, int):
        return globals.types["int"].build(node=node)
    if isinstance(v, float):
        return globals.types["float"].build(node=node)
    return None
