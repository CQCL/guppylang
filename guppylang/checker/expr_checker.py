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

from guppylang.ast_util import (
    AstNode,
    AstVisitor,
    breaks_in_loop,
    get_type_opt,
    name_nodes_in_ast,
    return_nodes_in_ast,
    with_loc,
    with_type,
)
from guppylang.checker.core import (
    Context,
    DummyEvalDict,
    Globals,
    Locals,
)
from guppylang.definition.ty import TypeDef
from guppylang.definition.value import CallableDef, ValueDef
from guppylang.error import (
    GuppyError,
    GuppyTypeError,
    GuppyTypeInferenceError,
    InternalGuppyError,
)
from guppylang.nodes import (
    DesugaredGenerator,
    DesugaredListComp,
    GlobalCall,
    GlobalName,
    IterEnd,
    IterHasNext,
    IterNext,
    LocalCall,
    LocalName,
    MakeIter,
    PyExpr,
    TensorCall,
    TypeApply,
)
from guppylang.tys.arg import TypeArg
from guppylang.tys.builtin import (
    bool_type,
    get_element_type,
    is_bool_type,
    is_linst_type,
    is_list_type,
    linst_type,
    list_type,
)
from guppylang.tys.param import TypeParam
from guppylang.tys.subst import Inst, Subst
from guppylang.tys.ty import (
    ExistentialTypeVar,
    FunctionType,
    NoneType,
    OpaqueType,
    TupleType,
    Type,
    TypeBase,
    function_tensor_signature,
    parse_function_tensor,
    row_to_type,
    unify,
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
        expected: Type,
        actual: ast.expr | Type,
        loc: AstNode | None = None,
    ) -> NoReturn:
        """Raises a type error indicating that the type doesn't match."""
        if not isinstance(actual, TypeBase):
            loc = loc or actual
            _, actual = self._synthesize(actual, allow_free_vars=True)
        if loc is None:
            raise InternalGuppyError("Failure location is required")
        raise GuppyTypeError(
            f"Expected {self._kind} of type `{expected}`, got `{actual}`", loc
        )

    def check(
        self, expr: ast.expr, ty: Type, kind: str = "expression"
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
    ) -> tuple[ast.expr, Type]:
        """Invokes the type synthesiser"""
        return ExprSynthesizer(self.ctx).synthesize(node, allow_free_vars)

    def visit_Tuple(self, node: ast.Tuple, ty: Type) -> tuple[ast.expr, Subst]:
        if not (isinstance(ty, TupleType) and len(ty.element_types) == len(node.elts)):
            return self._fail(ty, node)

        # Tuples can either be inert python tuples or tuples of functions which
        # can be called in guppy. The former thing is checkable, but in the
        # latter case we should be able to synthesise function types for the
        # elements. Check here whether the given type is a tuple of function
        # types to work out which case we're in.
        function_types = parse_function_tensor(ty)
        if not function_types:
            subst: Subst = {}
            for i, el in enumerate(node.elts):
                node.elts[i], s = self.check(el, ty.element_types[i].substitute(subst))
                subst |= s
            return node, subst
        else:
            assert isinstance(function_types, list)
            elem_tys: list[FunctionType] = []
            # The substitution for the whole tuple of function types
            big_subst: Subst = {}
            for i, (elt, elt_ty) in enumerate(zip(node.elts, function_types)):
                node.elts[i], fun_ty = self._synthesize(elt, allow_free_vars=True)
                assert isinstance(fun_ty, FunctionType)
                elem_tys.append(fun_ty)
                # Start with an empty substitution because the function types
                # should have independent variables
                subst = unify(fun_ty, elt_ty, {}) or {}
                big_subst |= {}

            return node, big_subst

    def visit_List(self, node: ast.List, ty: Type) -> tuple[ast.expr, Subst]:
        if not is_list_type(ty) and not is_linst_type(ty):
            return self._fail(ty, node)
        el_ty = get_element_type(ty)
        subst: Subst = {}
        for i, el in enumerate(node.elts):
            node.elts[i], s = self.check(el, el_ty.substitute(subst))
            subst |= s
        return node, subst

    def visit_DesugaredListComp(
        self, node: DesugaredListComp, ty: Type
    ) -> tuple[ast.expr, Subst]:
        if not is_list_type(ty) and not is_linst_type(ty):
            return self._fail(ty, node)
        node, elt_ty = synthesize_comprehension(node, node.generators, self.ctx)
        subst = unify(get_element_type(ty), elt_ty, {})
        if subst is None:
            actual = linst_type(elt_ty) if elt_ty.linear else list_type(elt_ty)
            return self._fail(ty, actual, node)
        return node, subst

    def visit_Call(self, node: ast.Call, ty: Type) -> tuple[ast.expr, Subst]:
        if len(node.keywords) > 0:
            raise GuppyError(
                "Argument passing by keyword is not supported", node.keywords[0]
            )
        node.func, func_ty = self._synthesize(node.func, allow_free_vars=False)

        # First handle direct calls of user-defined functions and extension functions
        if isinstance(node.func, GlobalName):
            defn = self.ctx.globals[node.func.def_id]
            if isinstance(defn, CallableDef):
                return defn.check_call(node.args, ty, node, self.ctx)

        # Otherwise, it must be a function as a higher-order value - something
        # whose type is either a FunctionType or a Tuple of FunctionTypes
        if isinstance(func_ty, FunctionType):
            args, return_ty, inst = check_call(func_ty, node.args, ty, node, self.ctx)
            check_inst(func_ty, inst, node)
            node.func = instantiate_poly(node.func, func_ty, inst)
            return with_loc(node, LocalCall(func=node.func, args=args)), return_ty

        if isinstance(func_ty, TupleType) and (
            function_elements := parse_function_tensor(func_ty)
        ):
            assert isinstance(function_elements, list)
            tensor_ty = function_tensor_signature(function_elements)

            remaining_args: list[ast.expr] = node.args
            call_nodes: list[GlobalCall | LocalCall] = []
            big_subst: Subst = {}
            if isinstance(node.func, ast.Tuple):
                for f, f_ty in zip(node.func.elts, func_ty.element_types):
                    assert isinstance(f_ty, FunctionType)
                    # Use the concrete output type of the function, we'll try to
                    # unify all of the results with `ty` at the end
                    processed_args, subst, inst, remaining_args = (
                        check_call_with_leftovers(
                            f_ty, remaining_args, f_ty.output, f, self.ctx
                        )
                    )
                    f_processed = instantiate_poly(f, f_ty, inst)

                    check_inst(f_ty, inst, node)
                    # Expect that each function is a `CallableDef`
                    if isinstance(f_processed, GlobalName):
                        assert isinstance(
                            self.ctx.globals[f_processed.def_id], CallableDef
                        )
                        call_nodes.append(
                            GlobalCall(
                                def_id=f_processed.def_id,
                                args=processed_args,
                                type_args=inst,
                            )
                        )
                    else:
                        call_nodes.append(
                            LocalCall(func=f_processed, args=processed_args)
                        )

                    big_subst |= subst

                    # If the substitution isn't empty, ...
                    subst = unify(ty, tensor_ty.output, big_subst) or big_subst

                return with_loc(node, TensorCall(call_nodes=call_nodes)), subst

            else:
                # The func isn't a tuple, it could be a call or a variable.
                # Here, the return type we expect has the outputs of all the
                # function types merged together, i.e.
                # f : Callable([A], tuple[B, C])
                # g : Callable([D], E)
                # (f, g)(a, d) : tuple[B, C, E]
                processed_args, big_subst, inst = check_call(
                    tensor_ty, node.args, tensor_ty.output, node.func, self.ctx
                )

                # TODO: instantiate a tuple of functions
                # f_processed = instantiate_poly(node.func, tensor_ty, inst)

                subst = unify(ty, tensor_ty.output, big_subst) or big_subst

                return with_loc(
                    node, LocalCall(func=node.func, args=processed_args)
                ), subst

        elif callee := self.ctx.globals.get_instance_func(func_ty, "__call__"):
            return callee.check_call(node.args, ty, node, self.ctx)
        else:
            raise GuppyTypeError(f"Expected function type, got `{func_ty}`", node.func)

    def visit_PyExpr(self, node: PyExpr, ty: Type) -> tuple[ast.expr, Subst]:
        python_val = eval_py_expr(node, self.ctx)
        if act := python_value_to_guppy_type(python_val, node, self.ctx.globals):
            subst = unify(ty, act, {})
            if subst is None:
                self._fail(ty, act, node)
            act = act.substitute(subst)
            subst = {x: s for x, s in subst.items() if x in ty.unsolved_vars}
            return with_type(act, with_loc(node, ast.Constant(value=python_val))), subst

        raise GuppyError(
            f"Python expression of type `{type(python_val)}` is not supported by Guppy",
            node,
        )

    def generic_visit(self, node: ast.expr, ty: Type) -> tuple[ast.expr, Subst]:
        # Try to synthesize and then check if we can unify it with the given type
        node, synth = self._synthesize(node, allow_free_vars=False)
        subst, inst = check_type_against(synth, ty, node, self._kind)

        # Apply instantiation of quantified type variables
        if inst:
            node = with_loc(node, TypeApply(value=node, inst=inst))

        return node, subst


class ExprSynthesizer(AstVisitor[tuple[ast.expr, Type]]):
    ctx: Context

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx

    def synthesize(
        self, node: ast.expr, allow_free_vars: bool = False
    ) -> tuple[ast.expr, Type]:
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
        self, expr: ast.expr, ty: Type, kind: str = "expression"
    ) -> tuple[ast.expr, Subst]:
        """Checks an expression against a given type"""
        return ExprChecker(self.ctx).check(expr, ty, kind)

    def visit_Constant(self, node: ast.Constant) -> tuple[ast.expr, Type]:
        ty = python_value_to_guppy_type(node.value, node, self.ctx.globals)
        if ty is None:
            raise GuppyError("Unsupported constant", node)
        return node, ty

    def visit_Name(self, node: ast.Name) -> tuple[ast.Name, Type]:
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
        elif x in self.ctx.globals:
            # Look-up what kind of definition it is
            match self.ctx.globals[x]:
                case ValueDef() as defn:
                    return with_loc(node, GlobalName(id=x, def_id=defn.id)), defn.ty
                # For types, we return their `__new__` constructor
                case TypeDef() as defn if constr := self.ctx.globals.get_instance_func(
                    defn, "__new__"
                ):
                    return with_loc(node, GlobalName(id=x, def_id=constr.id)), constr.ty
                case defn:
                    raise GuppyError(
                        f"Expected a value, got {defn.description} `{x}`", node
                    )
        raise InternalGuppyError(
            f"Variable `{x}` is not defined in `TypeSynthesiser`. This should have "
            "been caught by program analysis!"
        )

    def visit_Tuple(self, node: ast.Tuple) -> tuple[ast.expr, Type]:
        elems = [self.synthesize(elem) for elem in node.elts]

        node.elts = [n for n, _ in elems]
        return node, TupleType([ty for _, ty in elems])

    def visit_List(self, node: ast.List) -> tuple[ast.expr, Type]:
        if len(node.elts) == 0:
            raise GuppyTypeInferenceError(
                "Cannot infer type variable in expression of type `list[?T]`", node
            )
        node.elts[0], el_ty = self.synthesize(node.elts[0])
        node.elts[1:] = [self._check(el, el_ty)[0] for el in node.elts[1:]]
        return node, linst_type(el_ty) if el_ty.linear else list_type(el_ty)

    def visit_DesugaredListComp(self, node: DesugaredListComp) -> tuple[ast.expr, Type]:
        node, elt_ty = synthesize_comprehension(node, node.generators, self.ctx)
        result_ty = linst_type(elt_ty) if elt_ty.linear else list_type(elt_ty)
        return node, result_ty

    def visit_UnaryOp(self, node: ast.UnaryOp) -> tuple[ast.expr, Type]:
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
    ) -> tuple[ast.expr, Type]:
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
    ) -> tuple[ast.expr, Type]:
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
                f"Method `{ty}.{func_name}` has signature `{func.ty}`, but "
                f"expected `{exp_sig}`",
                node,
            )
        return func.synthesize_call([node, *args], node, self.ctx)

    def visit_BinOp(self, node: ast.BinOp) -> tuple[ast.expr, Type]:
        return self._synthesize_binary(node.left, node.right, node.op, node)

    def visit_Compare(self, node: ast.Compare) -> tuple[ast.expr, Type]:
        if len(node.comparators) != 1 or len(node.ops) != 1:
            raise InternalGuppyError(
                "BB contains chained comparison. Should have been removed during CFG "
                "construction."
            )
        left_expr, [op], [right_expr] = node.left, node.ops, node.comparators
        return self._synthesize_binary(left_expr, right_expr, op, node)

    def visit_Subscript(self, node: ast.Subscript) -> tuple[ast.expr, Type]:
        node.value, ty = self.synthesize(node.value)
        exp_sig = FunctionType(
            [ty, ExistentialTypeVar.fresh("Key", False)],
            ExistentialTypeVar.fresh("Val", False),
        )
        return self._synthesize_instance_func(
            node.value, [node.slice], "__getitem__", "not subscriptable", exp_sig
        )

    def visit_Call(self, node: ast.Call) -> tuple[ast.expr, Type]:
        if len(node.keywords) > 0:
            raise GuppyError("Keyword arguments are not supported", node.keywords[0])
        node.func, ty = self.synthesize(node.func)

        # First handle direct calls of user-defined functions and extension functions
        if isinstance(node.func, GlobalName):
            defn = self.ctx.globals[node.func.def_id]
            if isinstance(defn, CallableDef):
                return defn.synthesize_call(node.args, node, self.ctx)

        # Otherwise, it must be a function as a higher-order value, or a tensor
        if isinstance(ty, FunctionType):
            args, return_ty, inst = synthesize_call(ty, node.args, node, self.ctx)
            node.func = instantiate_poly(node.func, ty, inst)
            return with_loc(node, LocalCall(func=node.func, args=args)), return_ty
        elif (
            isinstance(ty, TupleType)
            and (function_elems := parse_function_tensor(ty))
            and isinstance(node.func, ast.Tuple)
        ):
            # Note: None of the function types in a tuple of functions will have
            # overlapping type arguments.
            assert isinstance(function_elems, list)
            func_ty = function_tensor_signature(function_elems)
            remaining_args = node.args
            return_tys: list[Type] = []
            processed_args: list[ast.expr] = []
            call_nodes: list[ast.expr] = []
            for func in node.func.elts:
                args, return_ty, inst, remaining_args = synthesize_call_with_leftovers(
                    func_ty, remaining_args, node, self.ctx
                )
                processed_args.extend(args)
                if isinstance(return_ty, TupleType):
                    return_tys.extend(return_ty.element_types)
                else:
                    return_tys.append(return_ty)

                if isinstance(func, GlobalName):
                    assert isinstance(self.ctx.globals[func.def_id], CallableDef)
                    call_nodes.append(
                        GlobalCall(def_id=func.def_id, args=args, type_args=inst)
                    )
                else:
                    call_nodes.append(LocalCall(func=func, args=args))

            call_node = TensorCall(call_nodes)
            return with_loc(node, call_node), TupleType(return_tys)

        elif f := self.ctx.globals.get_instance_func(ty, "__call__"):
            return f.synthesize_call(node.args, node, self.ctx)
        else:
            raise GuppyTypeError(f"Expected function type, got `{ty}`", node.func)

    def visit_MakeIter(self, node: MakeIter) -> tuple[ast.expr, Type]:
        node.value, ty = self.synthesize(node.value)
        exp_sig = FunctionType([ty], ExistentialTypeVar.fresh("Iter", False))
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

    def visit_IterHasNext(self, node: IterHasNext) -> tuple[ast.expr, Type]:
        node.value, ty = self.synthesize(node.value)
        exp_sig = FunctionType([ty], TupleType([bool_type(), ty]))
        return self._synthesize_instance_func(
            node.value, [], "__hasnext__", "not an iterator", exp_sig, True
        )

    def visit_IterNext(self, node: IterNext) -> tuple[ast.expr, Type]:
        node.value, ty = self.synthesize(node.value)
        exp_sig = FunctionType(
            [ty], TupleType([ExistentialTypeVar.fresh("T", False), ty])
        )
        return self._synthesize_instance_func(
            node.value, [], "__next__", "not an iterator", exp_sig, True
        )

    def visit_IterEnd(self, node: IterEnd) -> tuple[ast.expr, Type]:
        node.value, ty = self.synthesize(node.value)
        exp_sig = FunctionType([ty], NoneType())
        return self._synthesize_instance_func(
            node.value, [], "__end__", "not an iterator", exp_sig, True
        )

    def visit_ListComp(self, node: ast.ListComp) -> tuple[ast.expr, Type]:
        raise InternalGuppyError(
            "BB contains `ListComp`. Should have been removed during CFG"
            f"construction: `{ast.unparse(node)}`"
        )

    def visit_PyExpr(self, node: PyExpr) -> tuple[ast.expr, Type]:
        python_val = eval_py_expr(node, self.ctx)
        if ty := python_value_to_guppy_type(python_val, node, self.ctx.globals):
            return with_loc(node, ast.Constant(value=python_val)), ty

        raise GuppyError(
            f"Python expression of type `{type(python_val)}` is not supported by Guppy",
            node,
        )

    def visit_NamedExpr(self, node: ast.NamedExpr) -> tuple[ast.expr, Type]:
        raise InternalGuppyError(
            "BB contains `NamedExpr`. Should have been removed during CFG"
            f"construction: `{ast.unparse(node)}`"
        )

    def visit_BoolOp(self, node: ast.BoolOp) -> tuple[ast.expr, Type]:
        raise InternalGuppyError(
            "BB contains `BoolOp`. Should have been removed during CFG construction: "
            f"`{ast.unparse(node)}`"
        )

    def visit_IfExp(self, node: ast.IfExp) -> tuple[ast.expr, Type]:
        raise InternalGuppyError(
            "BB contains `IfExp`. Should have been removed during CFG construction: "
            f"`{ast.unparse(node)}`"
        )


def check_type_against(
    act: Type, exp: Type, node: AstNode, kind: str = "expression"
) -> tuple[Subst, Inst]:
    """Checks a type against another type.

    Returns a substitution for the free variables the expected type and an instantiation
    for the parameters in the actual type. Note that the expected type may not be
    parametrised and the actual type may not contain free unification variables.
    """
    assert not isinstance(exp, FunctionType) or not exp.parametrized
    assert not act.unsolved_vars

    # The actual type may be parametrised. In that case, we have to find an
    # instantiation to avoid higher-rank types.
    subst: Subst | None
    if isinstance(act, FunctionType) and act.parametrized:
        unquantified, free_vars = act.unquantified()
        subst = unify(exp, unquantified, {})
        if subst is None:
            raise GuppyTypeError(f"Expected {kind} of type `{exp}`, got `{act}`", node)
        # Check that we have found a valid instantiation for all params
        for i, v in enumerate(free_vars):
            if v not in subst:
                raise GuppyTypeInferenceError(
                    f"Expected {kind} of type `{exp}`, got `{act}`. Couldn't infer an "
                    f"instantiation for parameter `{act.params[i].name}` (higher-rank "
                    "polymorphic types are not supported)",
                    node,
                )
            if subst[v].unsolved_vars:
                raise GuppyTypeError(
                    f"Expected {kind} of type `{exp}`, got `{act}`. Can't instantiate "
                    f"parameter `{act.params[i]}` with type `{subst[v]}` containing "
                    "free variables",
                    node,
                )
        inst = [TypeArg(subst[v]) for v in free_vars]
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


def check_num_args_sufficient(exp: int, act: int, node: AstNode) -> None:
    """Checks that enough arguments have been passed to a function."""
    if act < exp:
        raise GuppyTypeError(
            f"Not enough arguments passed (expected {exp}, got {act})", node
        )


def check_leftovers_nil(
    args_checked: int, leftovers: list[ast.expr], node: AstNode
) -> None:
    if len(leftovers) > 0:
        if isinstance(node, ast.Call):
            raise GuppyTypeError("Unexpected argument", leftovers[0])
        total_args = args_checked + len(leftovers)
        msg = f"Too many arguments passed (expected {args_checked}, got {total_args})"
        raise GuppyTypeError(msg, node)


def type_check_args(
    inputs: list[ast.expr],
    func_ty: FunctionType,
    subst: Subst,
    ctx: Context,
    node: AstNode,
) -> tuple[list[ast.expr], Subst]:
    """Checks the arguments of a function call and infers free type variables.

    We expect that parameters have been replaced with free unification variables.
    Checks that all unification variables can be inferred.
    """
    exprs, subst, leftovers = type_check_args_with_leftovers(
        inputs, func_ty, subst, ctx, node
    )
    check_leftovers_nil(len(exprs), leftovers, node)
    return exprs, subst


def type_check_args_with_leftovers(
    inputs: list[ast.expr],
    func_ty: FunctionType,
    subst: Subst,
    ctx: Context,
    node: AstNode,
) -> tuple[list[ast.expr], Subst, list[ast.expr]]:
    """Checks the arguments of a function call and infers free type variables.

    We expect that parameters have been replaced with free unification variables.
    Checks that all unification variables can be inferred.
    """
    assert not func_ty.parametrized
    check_num_args_sufficient(len(func_ty.inputs), len(inputs), node)

    new_args: list[ast.expr] = []
    for ty, inp in zip(func_ty.inputs, inputs):
        a, s = ExprChecker(ctx).check(inp, ty.substitute(subst), "argument")
        new_args.append(a)
        subst |= s

    leftovers = inputs[len(func_ty.inputs) :]

    # If the argument check succeeded, this means that we must have found instantiations
    # for all unification variables occurring in the input types
    assert all(set.issubset(inp.unsolved_vars, subst.keys()) for inp in func_ty.inputs)

    # We also have to check that we found instantiations for all vars in the return type
    if not set.issubset(func_ty.output.unsolved_vars, subst.keys()):
        raise GuppyTypeInferenceError(
            f"Cannot infer type variable in expression of type "
            f"`{func_ty.output.substitute(subst)}`",
            node,
        )

    return new_args, subst, leftovers


def synthesize_call(
    func_ty: FunctionType, args: list[ast.expr], node: AstNode, ctx: Context
) -> tuple[list[ast.expr], Type, Inst]:
    exprs, tys, inst, leftovers = synthesize_call_with_leftovers(
        func_ty, args, node, ctx
    )
    check_leftovers_nil(len(exprs), leftovers, node)
    return exprs, tys, inst


def synthesize_call_with_leftovers(
    func_ty: FunctionType, args: list[ast.expr], node: AstNode, ctx: Context
) -> tuple[list[ast.expr], Type, Inst, list[ast.expr]]:
    """Synthesizes the return type of a function call.

    Returns an annotated argument list, the synthesized return type, and an
    instantiation for the quantifiers in the function type.
    """
    assert not func_ty.unsolved_vars
    check_num_args_sufficient(len(func_ty.inputs), len(args), node)

    # Replace quantified variables with free unification variables and try to infer an
    # instantiation by checking the arguments
    unquantified, free_vars = func_ty.unquantified()

    args, subst, leftovers = type_check_args_with_leftovers(
        args, unquantified, {}, ctx, node
    )

    # Success implies that the substitution is closed
    assert all(not t.unsolved_vars for t in subst.values())
    inst = [TypeArg(subst[v]) for v in free_vars]

    # Finally, check that the instantiation respects the linearity requirements
    check_inst(func_ty, inst, node)

    return args, unquantified.output.substitute(subst), inst, leftovers


def check_call(
    func_ty: FunctionType,
    inputs: list[ast.expr],
    ty: Type,
    node: AstNode,
    ctx: Context,
    kind: str = "expression",
) -> tuple[list[ast.expr], Subst, Inst]:
    exprs, subst, inst, leftovers = check_call_with_leftovers(
        func_ty, inputs, ty, node, ctx, kind
    )
    check_leftovers_nil(len(exprs), leftovers, node)
    return exprs, subst, inst


def check_call_with_leftovers(
    func_ty: FunctionType,
    inputs: list[ast.expr],
    ty: Type,
    node: AstNode,
    ctx: Context,
    kind: str = "expression",
) -> tuple[list[ast.expr], Subst, Inst, list[ast.expr]]:
    """Checks the return type of a function call against a given type.

    Returns an annotated argument list, a substitution for the free variables in the
    expected type, and an instantiation for the quantifiers in the function type.
    """
    assert not func_ty.unsolved_vars
    check_num_args_sufficient(len(func_ty.inputs), len(inputs), node)

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
    res: tuple[Type, Inst, list[ast.expr]] | None = None
    try:
        inputs, synth, inst, leftovers = synthesize_call_with_leftovers(
            func_ty, inputs, node, ctx
        )
        res = synth, inst, leftovers
    except GuppyTypeInferenceError:
        pass
    if res is not None:
        synth, inst, leftovers = res
        subst = unify(ty, synth, {})
        if subst is None:
            raise GuppyTypeError(f"Expected {kind} of type `{ty}`, got `{synth}`", node)
        return inputs, subst, inst, leftovers

    # If synthesis fails, we try again, this time also using information from the
    # expected return type
    unquantified, free_vars = func_ty.unquantified()
    subst = unify(ty, unquantified.output, {})
    if subst is None:
        raise GuppyTypeError(
            f"Expected {kind} of type `{ty}`, got `{unquantified.output}`", node
        )

    # Try to infer more by checking against the arguments
    inputs, subst, leftovers = type_check_args_with_leftovers(
        inputs, unquantified, subst, ctx, node
    )

    # Also make sure we found an instantiation for all free vars in the type we're
    # checking against
    if not set.issubset(ty.unsolved_vars, subst.keys()):
        raise GuppyTypeInferenceError(
            f"Expected expression of type `{ty}`, got "
            f"`{func_ty.output.substitute(subst)}`. Couldn't infer type variables",
            node,
        )

    # Success implies that the substitution is closed
    assert all(not t.unsolved_vars for t in subst.values())
    inst = [TypeArg(subst[v]) for v in free_vars]
    subst = {v: t for v, t in subst.items() if v in ty.unsolved_vars}

    # Finally, check that the instantiation respects the linearity requirements
    check_inst(func_ty, inst, node)

    return inputs, subst, inst, leftovers


def check_inst(func_ty: FunctionType, inst: Inst, node: AstNode) -> None:
    """Checks if an instantiation is valid.

    Makes sure that the linearity requirements are satisfied.
    """
    for param, arg in zip(func_ty.params, inst, strict=True):
        # Give a more informative error message for linearity issues
        if (
            isinstance(param, TypeParam)
            and isinstance(arg, TypeArg)
            and arg.ty.linear
            and not param.can_be_linear
        ):
            raise GuppyTypeError(
                f"Cannot instantiate non-linear type variable `{param.name}` in type "
                f"`{func_ty}` with linear type `{arg.ty}`",
                node,
            )
        # For everything else, we fall back to the default checking implementation
        param.check_arg(arg, node)


def instantiate_poly(node: ast.expr, ty: FunctionType, inst: Inst) -> ast.expr:
    """Instantiates quantified type arguments in a function."""
    assert len(ty.params) == len(inst)
    if len(inst) > 0:
        node = with_loc(node, TypeApply(value=with_type(ty, node), inst=inst))
        return with_type(ty.instantiate(inst), node)
    return with_type(ty, node)


def to_bool(node: ast.expr, node_ty: Type, ctx: Context) -> tuple[ast.expr, Type]:
    """Tries to turn a node into a bool"""
    if is_bool_type(node_ty):
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
    if not is_bool_type(return_ty):
        raise GuppyTypeError(
            f"`__bool__` on type `{node_ty}` returns `{return_ty}` instead of `bool`",
            node,
        )
    return call, return_ty


def synthesize_comprehension(
    node: DesugaredListComp, gens: list[DesugaredGenerator], ctx: Context
) -> tuple[DesugaredListComp, Type]:
    """Helper function to synthesise the element type of a list comprehension."""
    from guppylang.checker.stmt_checker import StmtChecker

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


def eval_py_expr(node: PyExpr, ctx: Context) -> Any:
    """Evaluates a `py(...)` expression."""
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
            DummyEvalDict(ctx, node.value),
        )
    except DummyEvalDict.GuppyVarUsedError as e:
        raise GuppyError(
            f"Guppy variable `{e.var}` cannot be accessed in a compile-time "
            "`py(...)` expression",
            e.node or node,
        ) from None
    except Exception as e:
        # Remove the top frame pointing to the `eval` call from the stack trace
        tb = e.__traceback__.tb_next if e.__traceback__ else None
        raise GuppyError(
            "Error occurred while evaluating Python expression:\n\n"
            + "".join(traceback.format_exception(type(e), e, tb)),
            node,
        ) from e
    return python_val


def python_value_to_guppy_type(v: Any, node: ast.expr, globals: Globals) -> Type | None:
    """Turns a primitive Python value into a Guppy type.

    Returns `None` if the Python value cannot be represented in Guppy.
    """
    match v:
        case bool():
            return bool_type()
        case int():
            return cast(TypeDef, globals["int"]).check_instantiate([])
        case float():
            return cast(TypeDef, globals["float"]).check_instantiate([])
        case tuple(elts):
            tys = [python_value_to_guppy_type(elt, node, globals) for elt in elts]
            if any(ty is None for ty in tys):
                return None
            return TupleType(cast(list[Type], tys))
        case list():
            return _python_list_to_guppy_type(v, node, globals)
        case _:
            # Pytket conversion is an optional feature
            try:
                import pytket

                if isinstance(v, pytket.circuit.Circuit):
                    # We also need tket2 installed
                    try:
                        import tket2  # type: ignore[import-untyped, import-not-found, unused-ignore]  # noqa: F401

                        qubit = cast(TypeDef, globals["qubit"]).check_instantiate([])
                        return FunctionType(
                            [qubit] * v.n_qubits,
                            row_to_type(
                                [qubit] * v.n_qubits + [bool_type()] * v.n_bits
                            ),
                        )
                    except ImportError:
                        raise GuppyError(
                            "Pytket compatibility requires `tket2` to be installed. "
                            "See https://github.com/CQCL/tket2/tree/main/tket2-py",
                            node,
                        ) from None
            except ImportError:
                pass
            return None


def _python_list_to_guppy_type(
    vs: list[Any], node: ast.expr, globals: Globals
) -> OpaqueType | None:
    """Turns a Python list into a Guppy type.

    Returns `None` if the list contains different types or types that are not
    representable in Guppy.
    """
    if len(vs) == 0:
        return list_type(ExistentialTypeVar.fresh("T", False))

    # All the list elements must have a unifiable types
    v, *rest = vs
    el_ty = python_value_to_guppy_type(v, node, globals)
    if el_ty is None:
        return None
    for v in rest:
        ty = python_value_to_guppy_type(v, node, globals)
        if ty is None:
            return None
        if (subst := unify(ty, el_ty, {})) is None:
            raise GuppyError("Python list contains elements with different types", node)
        el_ty = el_ty.substitute(subst)
    return list_type(el_ty)
