import ast
from typing import Optional, Union, NoReturn, Any

from guppy.ast_util import AstVisitor, with_loc, AstNode, with_type, get_type_opt
from guppy.checker.core import Context, CallableVariable, Globals
from guppy.error import (
    GuppyError,
    GuppyTypeError,
    InternalGuppyError,
    GuppyTypeInferenceError,
)
from guppy.gtypes import (
    GuppyType,
    TupleType,
    FunctionType,
    BoolType,
    Subst,
    FreeTypeVar,
    unify,
    Inst,
)
from guppy.nodes import LocalName, GlobalName, LocalCall, TypeApply

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


class ExprChecker(AstVisitor[tuple[ast.expr, Subst]]):
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
            _, actual = self._synthesize(actual, allow_free_vars=True)
        assert loc is not None
        raise GuppyTypeError(
            f"Expected {self._kind} of type `{expected}`, got `{actual}`", loc
        )

    def check(
        self, expr: ast.expr, ty: GuppyType, kind: str = "expression"
    ) -> tuple[ast.expr, Subst]:
        """Checks an expression against a type.

        The type may have free type variables which will try to be resolved. Returns
        a new desugared expression with type annotations and a substitution with the
        resolved type variables.
        """
        # When checking against a variable, we have to synthesize
        if isinstance(ty, FreeTypeVar):
            expr, syn_ty = self._synthesize(expr, allow_free_vars=False)
            return with_type(syn_ty, expr), {ty: syn_ty}

        # Otherwise, invoke the visitor
        old_kind = self._kind
        self._kind = kind or self._kind
        expr, subst = self.visit(expr, ty)
        self._kind = old_kind
        return with_type(ty.substitute(subst), expr), subst

    def _synthesize(
        self, node: ast.expr, allow_free_vars: bool
    ) -> tuple[ast.expr, GuppyType]:
        """Invokes the type synthesiser"""
        return ExprSynthesizer(self.ctx).synthesize(node, allow_free_vars)

    def visit_Tuple(self, node: ast.Tuple, ty: GuppyType) -> tuple[ast.expr, Subst]:
        if not isinstance(ty, TupleType) or len(ty.element_types) != len(node.elts):
            return self._fail(ty, node)
        subst: Subst = {}
        for i, el in enumerate(node.elts):
            node.elts[i], s = self.check(el, ty.element_types[i].substitute(subst))
            subst |= s
        return node, subst

    def visit_Call(self, node: ast.Call, ty: GuppyType) -> tuple[ast.expr, Subst]:
        if len(node.keywords) > 0:
            raise GuppyError(
                "Argument passing by keyword is not supported", node.keywords[0]
            )
        node.func, func_ty = self._synthesize(node.func, allow_free_vars=False)

        # First handle direct calls of user-defined functions and extension functions
        if isinstance(node.func, GlobalName) and isinstance(
            node.func.value, CallableVariable
        ):
            return node.func.value.check_call(node.args, ty, node, self.ctx)

        # Otherwise, it must be a function as a higher-order value
        if isinstance(func_ty, FunctionType):
            args, return_ty, inst = check_call(func_ty, node.args, ty, node, self.ctx)
            check_inst(func_ty, inst, node)
            node.func = instantiate_poly(node.func, func_ty, inst)
            return with_loc(node, LocalCall(func=node.func, args=args)), return_ty
        elif f := self.ctx.globals.get_instance_func(func_ty, "__call__"):
            return f.check_call(node.args, ty, node, self.ctx)
        else:
            raise GuppyTypeError(f"Expected function type, got `{func_ty}`", node.func)

    def generic_visit(  # type: ignore
        self, node: ast.expr, ty: GuppyType
    ) -> tuple[ast.expr, Subst]:
        # Try to synthesize and then check if we can unify it with the given type
        node, synth = self._synthesize(node, allow_free_vars=False)
        subst, inst = check_type_against(synth, ty, node, self._kind)

        # Apply instantiation of quantified type variables
        if inst:
            node = with_loc(node, TypeApply(value=node, tys=inst))

        return node, subst


class ExprSynthesizer(AstVisitor[tuple[ast.expr, GuppyType]]):
    ctx: Context

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx

    def synthesize(
        self, node: ast.expr, allow_free_vars: bool = False
    ) -> tuple[ast.expr, GuppyType]:
        """Tries to synthesise a type for the given expression.

        Also returns a new desugared expression with type annotations.
        """
        if ty := get_type_opt(node):
            return node, ty
        node, ty = self.visit(node)
        if ty.free_vars and not allow_free_vars:
            raise GuppyTypeError(
                f"Cannot infer type variable in expression of type `{ty}`", node
            )
        return with_type(ty, node), ty

    def _check(
        self, expr: ast.expr, ty: GuppyType, kind: str = "expression"
    ) -> tuple[ast.expr, Subst]:
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
            args, return_ty, inst = synthesize_call(ty, node.args, node, self.ctx)
            node.func = instantiate_poly(node.func, ty, inst)
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


def check_type_against(
    act: GuppyType, exp: GuppyType, node: AstNode, kind: str = "expression"
) -> tuple[Subst, Inst]:
    """Checks a type against another type.

    Returns a substitution for the free variables the expected type and an instantiation
    for the quantified variables in the actual type. Note that the expected type may not
    be quantified and the actual type may not contain free unification variables.
    """
    assert not isinstance(exp, FunctionType) or not exp.quantified
    assert not act.free_vars

    # The actual type may be quantified. In that case, we have to find an instantiation
    # to avoid higher-rank types.
    subst: Optional[Subst]
    if isinstance(act, FunctionType) and act.quantified:
        unquantified, free_vars = act.unquantified()
        subst = unify(exp, unquantified, {})
        if subst is None:
            raise GuppyTypeError(f"Expected {kind} of type `{exp}`, got `{act}`", node)
        # Check that we have found a valid instantiation for all quantified vars
        for i, v in enumerate(free_vars):
            if v not in subst:
                raise GuppyTypeInferenceError(
                    f"Expected {kind} of type `{exp}`, got `{act}`. Couldn't infer an "
                    f"instantiation for type variable `{act.quantified[i]}` (higher-"
                    "rank polymorphic types are not supported)",
                    node,
                )
            if subst[v].free_vars:
                raise GuppyTypeError(
                    f"Expected {kind} of type `{exp}`, got `{act}`. Can't instantiate "
                    f"type variable `{act.quantified[i]}` with type `{subst[v]}` "
                    "containing free variables",
                    node,
                )
        inst = [subst[v] for v in free_vars]
        subst = {v: t for v, t in subst.items() if v in exp.free_vars}

        # Finally, check that the instantiation respects the linearity requirements
        check_inst(act, inst, node)

        return subst, inst

    # Otherwise, we know that `act` has no free type vars, so unification is trivial
    assert not act.free_vars
    subst = unify(exp, act, {})
    if subst is None:
        raise GuppyTypeError(f"Expected {kind} of type `{exp}`, got `{act}`", node)
    return subst, []


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


def type_check_args(
    args: list[ast.expr],
    func_ty: FunctionType,
    subst: Subst,
    ctx: Context,
    node: AstNode,
) -> tuple[list[ast.expr], Subst]:
    """Checks the arguments of a function call and infers free type variables.

    We expect that quantified variables have been replaced with free unification
    variables. Checks that all unification variables can be inferred.
    """
    assert not func_ty.quantified
    check_num_args(len(func_ty.args), len(args), node)

    new_args: list[ast.expr] = []
    for arg, ty in zip(args, func_ty.args):
        a, s = ExprChecker(ctx).check(arg, ty.substitute(subst), "argument")
        new_args.append(a)
        subst |= s

    # If the argument check succeeded, this means that we must have found instantiations
    # for all unification variables occurring in the argument types
    assert all(set.issubset(arg.free_vars, subst.keys()) for arg in func_ty.args)

    # We also have to check that we found instantiations for all vars in the return type
    if not set.issubset(func_ty.returns.free_vars, subst.keys()):
        raise GuppyTypeInferenceError(
            f"Cannot infer type variable in expression of type "
            f"`{func_ty.returns.substitute(subst)}`",
            node,
        )

    return new_args, subst


def synthesize_call(
    func_ty: FunctionType, args: list[ast.expr], node: AstNode, ctx: Context
) -> tuple[list[ast.expr], GuppyType, Inst]:
    """Synthesizes the return type of a function call.

    Returns an annotated argument list, the synthesized return type, and an
    instantiation for the quantifiers in the function type.
    """
    assert not func_ty.free_vars
    check_num_args(len(func_ty.args), len(args), node)

    # Replace quantified variables with free unification variables and try to infer an
    # instantiation by checking the arguments
    unquantified, free_vars = func_ty.unquantified()
    args, subst = type_check_args(args, unquantified, {}, ctx, node)

    # Success implies that the substitution is closed
    assert all(not t.free_vars for t in subst.values())
    inst = [subst[v] for v in free_vars]

    # Finally, check that the instantiation respects the linearity requirements
    check_inst(func_ty, inst, node)

    return args, unquantified.returns.substitute(subst), inst


def check_call(
    func_ty: FunctionType,
    args: list[ast.expr],
    ty: GuppyType,
    node: AstNode,
    ctx: Context,
    kind: str = "expression",
) -> tuple[list[ast.expr], Subst, Inst]:
    """Checks the return type of a function call against a given type.

    Returns an annotated argument list, a substitution for the free variables in the
    expected type, and an instantiation for the quantifiers in the function type.
    """
    assert not func_ty.free_vars
    check_num_args(len(func_ty.args), len(args), node)

    # When checking, we can use the information from the expected return type to infer
    # some type arguments. However, this pushes errors inwards. For example, given a
    # function `foo: forall T. T -> T`, the following type mismatch would be reported:
    #
    #       x: int = foo(None)
    #                    ^^^^  Expected argument of type `int`, got `None`
    #
    # But the following error location would be more intuitive for users:
    #
    #       x: int = foo(None)
    #                ^^^^^^^^^  Expected expression of type `int`, got `None`
    #
    # In other words, if we can get away with synthesising the call without the extra
    # information from the expected type, we should do that to improve the error.

    # TODO: The approach below can result in exponential runtime in the worst case.
    #  However the bad case, e.g. `x: int = foo(foo(...foo(?)...))`, shouldn't be common
    #  in practice. Can we do better than that?

    # First, try to synthesize
    res: Optional[tuple[GuppyType, Inst]] = None
    try:
        args, synth, inst = synthesize_call(func_ty, args, node, ctx)
        res = synth, inst
    except GuppyTypeInferenceError:
        pass
    if res is not None:
        synth, inst = res
        subst = unify(ty, synth, {})
        if subst is None:
            raise GuppyTypeError(f"Expected {kind} of type `{ty}`, got `{synth}`", node)
        return args, subst, inst

    # If synthesis fails, we try again, this time also using information from the
    # expected return type
    unquantified, free_vars = func_ty.unquantified()
    subst = unify(ty, unquantified.returns, {})
    if subst is None:
        raise GuppyTypeError(
            f"Expected {kind} of type `{ty}`, got `{unquantified.returns}`", node
        )

    # Try to infer more by checking against the arguments
    args, subst = type_check_args(args, unquantified, subst, ctx, node)

    # Also make sure we found an instantiation for all free vars in the type we're
    # checking against
    if not set.issubset(ty.free_vars, subst.keys()):
        raise GuppyTypeInferenceError(
            f"Expected expression of type `{ty}`, got "
            f"`{func_ty.returns.substitute(subst)}`. Couldn't infer type variables",
            node,
        )

    # Success implies that the substitution is closed
    assert all(not t.free_vars for t in subst.values())
    inst = [subst[v] for v in free_vars]
    subst = {v: t for v, t in subst.items() if v in ty.free_vars}

    # Finally, check that the instantiation respects the linearity requirements
    check_inst(func_ty, inst, node)

    return args, subst, inst


def check_inst(func_ty: FunctionType, inst: Inst, node: AstNode) -> None:
    """Checks if an instantiation is valid.

    Makes sure that the linearity requirements are satisfied.
    """
    for var, ty in zip(func_ty.quantified, inst):
        if not var.linear and ty.linear:
            raise GuppyTypeError(
                f"Cannot instantiate non-linear type variable `{var}` in type "
                f"`{func_ty}` with linear type `{ty}`",
                node,
            )


def instantiate_poly(node: ast.expr, ty: FunctionType, inst: Inst) -> ast.expr:
    """Instantiates quantified type arguments in a function."""
    assert len(ty.quantified) == len(inst)
    if len(inst) > 0:
        node = with_loc(node, TypeApply(value=with_type(ty, node), tys=inst))
        return with_type(ty.instantiate(inst), node)
    return node


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
