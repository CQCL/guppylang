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

Expressions can be checked against a given type by the `ExprChecker`, raising a type
error if the expressions doesn't have the expected type. Checking is used for annotated
assignments, return values, and function arguments. Alternatively, the `ExprSynthesizer`
can be used to infer a type for an expression.
"""

import ast
import sys
import traceback
from contextlib import suppress
from typing import Any, NoReturn, cast

from guppy.ast_util import (
    AstNode,
    AstVisitor,
    breaks_in_loop,
    get_type_opt,
    name_nodes_in_ast,
    return_nodes_in_ast,
    with_loc,
    with_type,
)
from guppy.checker.core import CallableVariable, Context, DummyEvalDict, Globals, Locals
from guppy.error import (
    GuppyError,
    GuppyTypeError,
    GuppyTypeInferenceError,
    InternalGuppyError,
)
from guppy.gtypes import (
    BoolType,
    ExistentialTypeVar,
    FunctionType,
    GuppyType,
    Inst,
    LinstType,
    ListType,
    NoneType,
    Subst,
    TupleType,
    unify,
)
from guppy.nodes import (
    DesugaredGenerator,
    DesugaredListComp,
    GlobalName,
    IterEnd,
    IterHasNext,
    IterNext,
    LocalCall,
    LocalName,
    MakeIter,
    PyExpr,
    TypeApply,
)

# Mapping from unary AST op to dunder method and display name
unary_table: dict[type[ast.unaryop], tuple[str, str]] = {
    ast.UAdd:   ("__pos__",    "+"),
    ast.USub:   ("__neg__",    "-"),
    ast.Invert: ("__invert__", "~"),
}  # fmt: skip

# Mapping from binary AST op to left dunder method, right dunder method and display name
AstOp = ast.operator | ast.cmpop
binary_table: dict[type[AstOp], tuple[str, str, str]] = {
    ast.Add:      ("__add__",      "__radd__",      "+"),
    ast.Sub:      ("__sub__",      "__rsub__",      "-"),
    ast.Mult:     ("__mul__",      "__rmul__",      "*"),
    ast.Div:      ("__truediv__",  "__rtruediv__",  "/"),
    ast.FloorDiv: ("__floordiv__", "__rfloordiv__", "//"),
    ast.Mod:      ("__mod__",      "__rmod__",      "%"),
    ast.Pow:      ("__pow__",      "__rpow__",      "**"),
    ast.LShift:   ("__lshift__",   "__rlshift__",   "<<"),
    ast.RShift:   ("__rshift__",   "__rrshift__",   ">>"),
    ast.BitOr:    ("__or__",       "__ror__",       "|"),
    ast.BitXor:   ("__xor__",      "__rxor__",      "^"),
    ast.BitAnd:   ("__and__",      "__rand__",      "&"),
    ast.MatMult:  ("__matmul__",   "__rmatmul__",   "@"),
    ast.Eq:       ("__eq__",       "__eq__",        "=="),
    ast.NotEq:    ("__neq__",      "__neq__",       "!="),
    ast.Lt:       ("__lt__",       "__gt__",        "<"),
    ast.LtE:      ("__le__",       "__ge__",        "<="),
    ast.Gt:       ("__gt__",       "__lt__",        ">"),
    ast.GtE:      ("__ge__",       "__le__",        ">="),
}  # fmt: skip


class ExprChecker(AstVisitor[tuple[ast.expr, Subst]]):
    """Checks an expression against a type and produces a new type-annotated AST.

    The type may contain free variables that the checker will try to solve. Note that
    the checker will fail, if some free variables cannot be inferred.
    """

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
        actual: ast.expr | GuppyType,
        loc: AstNode | None = None,
    ) -> NoReturn:
        """Raises a type error indicating that the type doesn't match."""
        if not isinstance(actual, GuppyType):
            loc = loc or actual
            _, actual = self._synthesize(actual, allow_free_vars=True)
        if loc is None:
            raise InternalGuppyError("Failure location is required")
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
        # If we already have a type for the expression, we just have to match it against
        # the target
        if actual := get_type_opt(expr):
            subst, inst = check_type_against(actual, ty, expr, kind)
            if inst:
                expr = with_loc(expr, TypeApply(value=expr, tys=inst))
            return with_type(ty.substitute(subst), expr), subst

        # When checking against a variable, we have to synthesize
        if isinstance(ty, ExistentialTypeVar):
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

    def visit_List(self, node: ast.List, ty: GuppyType) -> tuple[ast.expr, Subst]:
        if not isinstance(ty, ListType | LinstType):
            return self._fail(ty, node)
        subst: Subst = {}
        for i, el in enumerate(node.elts):
            node.elts[i], s = self.check(el, ty.element_type.substitute(subst))
            subst |= s
        return node, subst

    def visit_DesugaredListComp(
        self, node: DesugaredListComp, ty: GuppyType
    ) -> tuple[ast.expr, Subst]:
        if not isinstance(ty, ListType | LinstType):
            return self._fail(ty, node)
        node, elt_ty = synthesize_comprehension(node, node.generators, self.ctx)
        subst = unify(ty.element_type, elt_ty, {})
        if subst is None:
            actual = LinstType(elt_ty) if elt_ty.linear else ListType(elt_ty)
            return self._fail(ty, actual, node)
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

    def generic_visit(self, node: ast.expr, ty: GuppyType) -> tuple[ast.expr, Subst]:
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
        if ty.unsolved_vars and not allow_free_vars:
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

    def visit_Name(self, node: ast.Name) -> tuple[ast.Name, GuppyType]:
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

    def visit_List(self, node: ast.List) -> tuple[ast.expr, GuppyType]:
        if len(node.elts) == 0:
            raise GuppyTypeInferenceError(
                "Cannot infer type variable in expression of type `list[?T]`", node
            )
        node.elts[0], el_ty = self.synthesize(node.elts[0])
        node.elts[1:] = [self._check(el, el_ty)[0] for el in node.elts[1:]]
        return node, LinstType(el_ty) if el_ty.linear else ListType(el_ty)

    def visit_DesugaredListComp(
        self, node: DesugaredListComp
    ) -> tuple[ast.expr, GuppyType]:
        node, elt_ty = synthesize_comprehension(node, node.generators, self.ctx)
        result_ty = LinstType(elt_ty) if elt_ty.linear else ListType(elt_ty)
        return node, result_ty

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
            with suppress(GuppyError):
                return func.synthesize_call([left_expr, right_expr], node, self.ctx)

        if func := self.ctx.globals.get_instance_func(right_ty, rop):
            with suppress(GuppyError):
                return func.synthesize_call([right_expr, left_expr], node, self.ctx)

        raise GuppyTypeError(
            f"Binary operator `{display_name}` not defined for arguments of type "
            f"`{left_ty}` and `{right_ty}`",
            node,
        )

    def _synthesize_instance_func(
        self,
        node: ast.expr,
        args: list[ast.expr],
        func_name: str,
        err: str,
        exp_sig: FunctionType | None = None,
        give_reason: bool = False,
    ) -> tuple[ast.expr, GuppyType]:
        """Helper method for expressions that are implemented via instance methods.

        Raises a `GuppyTypeError` if the given instance method is not defined. The error
        message can be customised by passing an `err` string and an optional error
        reason can be printed.

        Optionally, the signature of the instance function can also be checked against a
        given expected signature.
        """
        node, ty = self.synthesize(node)
        func = self.ctx.globals.get_instance_func(ty, func_name)
        if func is None:
            reason = f" since it does not implement the `{func_name}` method"
            raise GuppyTypeError(
                f"Expression of type `{ty}` is {err}{reason if give_reason else ''}",
                node,
            )
        if exp_sig and unify(exp_sig, func.ty.unquantified()[0], {}) is None:
            raise GuppyError(
                f"Method `{ty.name}.{func_name}` has signature `{func.ty}`, but "
                f"expected `{exp_sig}`",
                node,
            )
        return func.synthesize_call([node, *args], node, self.ctx)

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

    def visit_Subscript(self, node: ast.Subscript) -> tuple[ast.expr, GuppyType]:
        node.value, ty = self.synthesize(node.value)
        exp_sig = FunctionType(
            [ty, ExistentialTypeVar.new("Key", False)],
            ExistentialTypeVar.new("Val", False),
        )
        return self._synthesize_instance_func(
            node.value, [node.slice], "__getitem__", "not subscriptable", exp_sig
        )

    def visit_Call(self, node: ast.Call) -> tuple[ast.expr, GuppyType]:
        if len(node.keywords) > 0:
            raise GuppyError("Keyword arguments are not supported", node.keywords[0])
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

    def visit_MakeIter(self, node: MakeIter) -> tuple[ast.expr, GuppyType]:
        node.value, ty = self.synthesize(node.value)
        exp_sig = FunctionType([ty], ExistentialTypeVar.new("Iter", False))
        expr, ty = self._synthesize_instance_func(
            node.value, [], "__iter__", "not iterable", exp_sig
        )

        # If the iterator was created by a `for` loop, we can add some extra checks to
        # produce nicer errors for linearity violations. Namely, `break` and `return`
        # are not allowed when looping over a linear iterator (`continue` is allowed)
        if ty.linear and isinstance(node.origin_node, ast.For):
            breaks = breaks_in_loop(node.origin_node) or return_nodes_in_ast(
                node.origin_node
            )
            if breaks:
                raise GuppyTypeError(
                    f"Loop over iterator with linear type `{ty}` cannot be terminated "
                    f"prematurely",
                    breaks[0],
                )
        return expr, ty

    def visit_IterHasNext(self, node: IterHasNext) -> tuple[ast.expr, GuppyType]:
        node.value, ty = self.synthesize(node.value)
        exp_sig = FunctionType([ty], TupleType([BoolType(), ty]))
        return self._synthesize_instance_func(
            node.value, [], "__hasnext__", "not an iterator", exp_sig, True
        )

    def visit_IterNext(self, node: IterNext) -> tuple[ast.expr, GuppyType]:
        node.value, ty = self.synthesize(node.value)
        exp_sig = FunctionType(
            [ty], TupleType([ExistentialTypeVar.new("T", False), ty])
        )
        return self._synthesize_instance_func(
            node.value, [], "__next__", "not an iterator", exp_sig, True
        )

    def visit_IterEnd(self, node: IterEnd) -> tuple[ast.expr, GuppyType]:
        node.value, ty = self.synthesize(node.value)
        exp_sig = FunctionType([ty], NoneType())
        return self._synthesize_instance_func(
            node.value, [], "__end__", "not an iterator", exp_sig, True
        )

    def visit_ListComp(self, node: ast.ListComp) -> tuple[ast.expr, GuppyType]:
        raise InternalGuppyError(
            "BB contains `ListComp`. Should have been removed during CFG"
            f"construction: `{ast.unparse(node)}`"
        )

    def visit_PyExpr(self, node: PyExpr) -> tuple[ast.expr, GuppyType]:
        # The method we used for obtaining the Python variables in scope only works in
        # CPython (see `get_py_scope()`).
        if sys.implementation.name != "cpython":
            raise GuppyError(
                "Compile-time `py(...)` expressions are only supported in CPython", node
            )

        try:
            python_val = eval(  # noqa: S307, PGH001
                ast.unparse(node.value),
                None,
                DummyEvalDict(self.ctx, node.value),
            )
        except DummyEvalDict.GuppyVarUsedError as e:
            raise GuppyError(
                f"Guppy variable `{e.var}` cannot be accessed in a compile-time "
                "`py(...)` expression",
                e.node or node,
            ) from None
        except Exception as e:  # noqa: BLE001
            # Remove the top frame pointing to the `eval` call from the stack trace
            tb = e.__traceback__.tb_next if e.__traceback__ else None
            raise GuppyError(
                "Error occurred while evaluating Python expression:\n\n"
                + "".join(traceback.format_exception(type(e), e, tb)),
                node,
            ) from e

        if ty := python_value_to_guppy_type(python_val, node, self.ctx.globals):
            return with_loc(node, ast.Constant(value=python_val)), ty

        raise GuppyError(
            f"Python expression of type `{type(python_val)}` is not supported by Guppy",
            node,
        )

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
    assert not act.unsolved_vars

    # The actual type may be quantified. In that case, we have to find an instantiation
    # to avoid higher-rank types.
    subst: Subst | None
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
            if subst[v].unsolved_vars:
                raise GuppyTypeError(
                    f"Expected {kind} of type `{exp}`, got `{act}`. Can't instantiate "
                    f"type variable `{act.quantified[i]}` with type `{subst[v]}` "
                    "containing free variables",
                    node,
                )
        inst = [subst[v] for v in free_vars]
        subst = {v: t for v, t in subst.items() if v in exp.unsolved_vars}

        # Finally, check that the instantiation respects the linearity requirements
        check_inst(act, inst, node)

        return subst, inst

    # Otherwise, we know that `act` has no unsolved type vars, so unification is trivial
    assert not act.unsolved_vars
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
    assert all(set.issubset(arg.unsolved_vars, subst.keys()) for arg in func_ty.args)

    # We also have to check that we found instantiations for all vars in the return type
    if not set.issubset(func_ty.returns.unsolved_vars, subst.keys()):
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
    assert not func_ty.unsolved_vars
    check_num_args(len(func_ty.args), len(args), node)

    # Replace quantified variables with free unification variables and try to infer an
    # instantiation by checking the arguments
    unquantified, free_vars = func_ty.unquantified()
    args, subst = type_check_args(args, unquantified, {}, ctx, node)

    # Success implies that the substitution is closed
    assert all(not t.unsolved_vars for t in subst.values())
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
    assert not func_ty.unsolved_vars
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
    res: tuple[GuppyType, Inst] | None = None
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
    if not set.issubset(ty.unsolved_vars, subst.keys()):
        raise GuppyTypeInferenceError(
            f"Expected expression of type `{ty}`, got "
            f"`{func_ty.returns.substitute(subst)}`. Couldn't infer type variables",
            node,
        )

    # Success implies that the substitution is closed
    assert all(not t.unsolved_vars for t in subst.values())
    inst = [subst[v] for v in free_vars]
    subst = {v: t for v, t in subst.items() if v in ty.unsolved_vars}

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


def synthesize_comprehension(
    node: DesugaredListComp, gens: list[DesugaredGenerator], ctx: Context
) -> tuple[DesugaredListComp, GuppyType]:
    """Helper function to synthesise the element type of a list comprehension."""
    from guppy.checker.stmt_checker import StmtChecker

    def check_linear_use_from_outer_scope(expr: ast.expr, locals: Locals) -> None:
        """Checks if an expression uses a linear variable from an outer scope.

        Since the expression is executed multiple times in the inner scope, this would
        mean that the outer linear variable is used multiple times, which is not
        allowed.
        """
        for name in name_nodes_in_ast(expr):
            x = name.id
            if x in locals and x not in locals.vars:
                var = locals[x]
                if var.ty.linear:
                    raise GuppyTypeError(
                        f"Variable `{x}` with linear type `{var.ty}` would be used "
                        "multiple times when evaluating this comprehension",
                        name,
                    )

    # If there are no more generators left, we can check the list element
    if not gens:
        node.elt, elt_ty = ExprSynthesizer(ctx).synthesize(node.elt)
        check_linear_use_from_outer_scope(node.elt, ctx.locals)
        return node, elt_ty

    # Check the iterator in the outer context
    gen, *gens = gens
    gen.iter_assign = StmtChecker(ctx).visit_Assign(gen.iter_assign)
    check_linear_use_from_outer_scope(gen.iter_assign.value, ctx.locals)

    # The rest is checked in a new nested context to ensure that variables don't escape
    # their scope
    inner_locals = Locals({}, parent_scope=ctx.locals)
    inner_ctx = Context(ctx.globals, inner_locals)
    expr_sth, stmt_chk = ExprSynthesizer(inner_ctx), StmtChecker(inner_ctx)
    gen.hasnext_assign = stmt_chk.visit_Assign(gen.hasnext_assign)
    gen.next_assign = stmt_chk.visit_Assign(gen.next_assign)
    gen.hasnext, hasnext_ty = expr_sth.visit_Name(gen.hasnext)
    gen.hasnext = with_type(hasnext_ty, gen.hasnext)
    gen.iter, iter_ty = expr_sth.visit_Name(gen.iter)
    gen.iter = with_type(iter_ty, gen.iter)

    # `if` guards are generally not allowed when we're iterating over linear variables.
    # The only exception is if all linear variables are already consumed by the first
    # guard
    if gen.ifs:
        gen.ifs[0], _ = expr_sth.synthesize(gen.ifs[0])

        # Now, check if there are linear iteration variables that have not been used by
        # the first guard
        for target in name_nodes_in_ast(gen.next_assign.targets[0]):
            var = inner_ctx.locals[target.id]
            if var.ty.linear and not var.used and gen.ifs:
                raise GuppyTypeError(
                    f"Variable `{var.name}` with linear type `{var.ty}` is not used on "
                    "all control-flow paths of the list comprehension",
                    target,
                )

        # Now, we can properly check all guards
        for i in range(len(gen.ifs)):
            gen.ifs[i], if_ty = expr_sth.synthesize(gen.ifs[i])
            gen.ifs[i], _ = to_bool(gen.ifs[i], if_ty, inner_ctx)
            check_linear_use_from_outer_scope(gen.ifs[i], inner_locals)

    # Check remaining generators
    node, elt_ty = synthesize_comprehension(node, gens, inner_ctx)

    # We have to make sure that all linear variables that were introduced in this scope
    # have been used
    for x, var in inner_ctx.locals.vars.items():
        if var.ty.linear and not var.used:
            raise GuppyTypeError(
                f"Variable `{x}` with linear type `{var.ty}` is not used",
                var.defined_at,
            )

    # The iter finalizer is again checked in the outer context
    ctx.locals[gen.iter.id].used = None
    gen.iterend, iterend_ty = ExprSynthesizer(ctx).synthesize(gen.iterend)
    gen.iterend = with_type(iterend_ty, gen.iterend)
    return node, elt_ty


def python_value_to_guppy_type(
    v: Any, node: ast.expr, globals: Globals
) -> GuppyType | None:
    """Turns a primitive Python value into a Guppy type.

    Returns `None` if the Python value cannot be represented in Guppy.
    """
    match v:
        case bool():
            return globals.types["bool"].build(node=node)
        case int():
            return globals.types["int"].build(node=node)
        case float():
            return globals.types["float"].build(node=node)
        case tuple(elts):
            tys = [python_value_to_guppy_type(elt, node, globals) for elt in elts]
            if any(ty is None for ty in tys):
                return None
            return TupleType(cast(list[GuppyType], tys))
        case _:
            return None
