"""Linearity checking

Linearity checking across control-flow is done by the `CFGChecker`.
"""

import ast
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from typing import TypeGuard

from guppylang.ast_util import AstNode, find_nodes, get_type
from guppylang.cfg.analysis import LivenessAnalysis
from guppylang.cfg.bb import BB, VariableStats
from guppylang.checker.cfg_checker import CheckedBB, CheckedCFG, Row, Signature
from guppylang.checker.core import (
    FieldAccess,
    Globals,
    Locals,
    Place,
    PlaceId,
    Variable,
)
from guppylang.definition.custom import CustomFunctionDef
from guppylang.definition.value import CallableDef
from guppylang.error import GuppyError, GuppyTypeError
from guppylang.nodes import (
    CheckedNestedFunctionDef,
    DesugaredGenerator,
    DesugaredListComp,
    FieldAccessAndDrop,
    GlobalCall,
    InoutReturnSentinel,
    LocalCall,
    PartialApply,
    PlaceNode,
    TensorCall,
)
from guppylang.tys.ty import FuncInput, FunctionType, InputFlags, StructType


class Scope(Locals[PlaceId, Place]):
    """Scoped collection of assigned places indexed by their id.

    Keeps track of which places have already been used.
    """

    parent_scope: "Scope | None"
    used_local: dict[PlaceId, AstNode]
    used_parent: dict[PlaceId, AstNode]

    def __init__(self, parent: "Scope | None" = None):
        self.used_local = {}
        self.used_parent = {}
        super().__init__({}, parent)

    def used(self, x: PlaceId) -> AstNode | None:
        """Checks whether a place has already been used."""
        if x in self.vars:
            return self.used_local.get(x, None)
        assert self.parent_scope is not None
        return self.parent_scope.used(x)

    def use(self, x: PlaceId, node: AstNode) -> None:
        """Records a use of a place.

        Works for places in the current scope as well as places in any parent scope.
        """
        if x in self.vars:
            self.used_local[x] = node
        else:
            assert self.parent_scope is not None
            assert x in self.parent_scope
            self.used_parent[x] = node
            self.parent_scope.use(x, node)

    def assign(self, place: Place) -> None:
        """Records an assignment of a place."""
        assert place.defined_at is not None
        x = place.id
        self.vars[x] = place
        if x in self.used_local:
            self.used_local.pop(x)

    def stats(self) -> VariableStats[PlaceId]:
        assigned = {}
        for x, place in self.vars.items():
            assert place.defined_at is not None
            assigned[x] = place.defined_at
        return VariableStats(assigned, self.used_parent)


class BBLinearityChecker(ast.NodeVisitor):
    """AST visitor that checks linearity for a single basic block."""

    scope: Scope
    stats: VariableStats[PlaceId]
    globals: Globals

    def check(
        self, bb: "CheckedBB[Variable]", is_entry: bool, globals: Globals
    ) -> Scope:
        # Manufacture a scope that holds all places that are live at the start
        # of this BB
        input_scope = Scope()
        for var in bb.sig.input_row:
            for place in leaf_places(var):
                input_scope.assign(place)
        self.globals = globals

        # Open up a new nested scope to check the BB contents. This way we can track
        # when we use variables from the outside vs ones assigned in this BB. The only
        # exception is the entry BB since function arguments should be treated as part
        # of the entry BB
        self.scope = input_scope if is_entry else Scope(input_scope)

        for stmt in bb.statements:
            self.visit(stmt)
        if bb.branch_pred:
            self.visit(bb.branch_pred)
        return self.scope

    @contextmanager
    def new_scope(self) -> Generator[Scope, None, None]:
        scope, new_scope = self.scope, Scope(self.scope)
        self.scope = new_scope
        yield new_scope
        self.scope = scope

    def visit_PlaceNode(self, node: PlaceNode, /, is_inout_arg: bool = False) -> None:
        # Usage of @inout variables is generally forbidden. The only exception is using
        # them in another @inout position of a function call. In that case, our
        # `_visit_call_args` helper will set `is_inout_arg=True`.
        if is_inout_var(node.place) and not is_inout_arg:
            raise GuppyError(
                f"{node.place.describe} may only be used in an `@inout` position since "
                "it is annotated as `@inout`. Consider removing the annotation to get "
                "ownership of the value.",
                node,
            )
        for place in leaf_places(node.place):
            x = place.id
            if (use := self.scope.used(x)) and place.ty.linear:
                raise GuppyError(
                    f"{place.describe} with linear type `{place.ty}` was already "
                    "used (at {0})",
                    node,
                    [use],
                )
            self.scope.use(x, node)

    def visit_Assign(self, node: ast.Assign) -> None:
        self.visit(node.value)
        self._check_assign_targets(node.targets)

    def _visit_call_args(self, func_ty: FunctionType, args: list[ast.expr]) -> None:
        """Helper function to check the arguments of a function call.

        Populates the `is_inout_arg` kwarg of `visit_PlaceNode` in case some of the
        arguments are places.
        """
        for inp, arg in zip(func_ty.inputs, args, strict=True):
            if isinstance(arg, PlaceNode):
                self.visit_PlaceNode(arg, is_inout_arg=InputFlags.Inout in inp.flags)
            else:
                self.visit(arg)

    def _reassign_inout_args(self, func_ty: FunctionType, args: list[ast.expr]) -> None:
        """Helper function to reassign the @inout arguments after a function call."""
        for inp, arg in zip(func_ty.inputs, args, strict=True):
            if InputFlags.Inout in inp.flags:
                match arg:
                    case PlaceNode(place=place):
                        for leaf in leaf_places(place):
                            leaf = leaf.replace_defined_at(arg)
                            self.scope.assign(leaf)
                    case arg if inp.ty.linear:
                        raise GuppyError(
                            f"Inout argument with linear type `{inp.ty}` would be "
                            "dropped after this function call. Consider assigning the "
                            "expression to a local variable before passing it to the "
                            "function.",
                            arg,
                        )

    def visit_GlobalCall(self, node: GlobalCall) -> None:
        func = self.globals[node.def_id]
        assert isinstance(func, CallableDef)
        if isinstance(func, CustomFunctionDef) and not func.has_signature:
            func_ty = FunctionType(
                [FuncInput(get_type(arg), InputFlags.NoFlags) for arg in node.args],
                get_type(node),
            )
        else:
            func_ty = func.ty.instantiate(node.type_args)
        self._visit_call_args(func_ty, node.args)
        self._reassign_inout_args(func_ty, node.args)

    def visit_LocalCall(self, node: LocalCall) -> None:
        func_ty = get_type(node.func)
        assert isinstance(func_ty, FunctionType)
        self.visit(node.func)
        self._visit_call_args(func_ty, node.args)
        self._reassign_inout_args(func_ty, node.args)

    def visit_TensorCall(self, node: TensorCall) -> None:
        for arg in node.args:
            self.visit(arg)
        self._reassign_inout_args(node.tensor_ty, node.args)

    def visit_PartialApply(self, node: PartialApply) -> None:
        self.visit(node.func)
        for arg in node.args:
            ty = get_type(arg)
            if ty.linear:
                raise GuppyError(
                    f"Capturing a value with linear type `{ty}` in a closure is not "
                    "allowed. Try calling the function directly instead of using it as "
                    "a higher-order value.",
                    node,
                )
            self.visit(arg)

    def visit_FieldAccessAndDrop(self, node: FieldAccessAndDrop) -> None:
        # A field access on a value that is not a place. This means the value can no
        # longer be accessed after the field has been projected out. Thus, this is only
        # legal if there are no remaining linear fields on the value
        self.visit(node.value)
        for field in node.struct_ty.fields:
            if field.name != node.field.name and field.ty.linear:
                raise GuppyTypeError(
                    f"Linear field `{field.name}` of expression with type "
                    f"`{node.struct_ty}` is not used",
                    node.value,
                )

    def visit_Expr(self, node: ast.Expr) -> None:
        # An expression statement where the return value is discarded
        self.visit(node.value)
        ty = get_type(node.value)
        if ty.linear:
            raise GuppyTypeError(f"Value with linear type `{ty}` is not used", node)

    def visit_DesugaredListComp(self, node: DesugaredListComp) -> None:
        self._check_comprehension(node, node.generators)

    def visit_CheckedNestedFunctionDef(self, node: CheckedNestedFunctionDef) -> None:
        # Linearity of the nested function has already been checked. We just need to
        # verify that no linear variables are captured
        # TODO: In the future, we could support capturing of non-linear subplaces
        for var, use in node.captured.values():
            if var.ty.linear:
                raise GuppyError(
                    f"{var.describe} with linear type `{var.ty}` may not be used here "
                    f"because it was defined in an outer scope (at {{0}})",
                    use,
                    [var.defined_at],
                )
            for place in leaf_places(var):
                self.scope.use(place.id, use)
        self.scope.assign(Variable(node.name, node.ty, node))

    def _check_assign_targets(self, targets: list[ast.expr]) -> None:
        """Helper function to check assignments."""
        # We're not allowed to override an unused linear place
        [target] = targets
        for tgt in find_nodes(lambda n: isinstance(n, PlaceNode), target):
            assert isinstance(tgt, PlaceNode)
            # Special error message for shadowing of @inout vars
            x = tgt.place.id
            if x in self.scope.vars and is_inout_var(self.scope[x]):
                raise GuppyError(
                    f"Assignment shadows argument `{tgt.place}` annotated as `@inout`. "
                    "Consider assigning to a different name.",
                    tgt,
                )
            for tgt_place in leaf_places(tgt.place):
                x = tgt_place.id
                # Only check for overrides of places locally defined in this BB. Global
                # checks are handled by dataflow analysis.
                if x in self.scope.vars and x not in self.scope.used_local:
                    place = self.scope[x]
                    if place.ty.linear:
                        raise GuppyError(
                            f"{place.describe} with linear type `{place.ty}` is not "
                            "used",
                            place.defined_at,
                        )
                self.scope.assign(tgt_place)

    def _check_comprehension(
        self, node: DesugaredListComp, gens: list[DesugaredGenerator]
    ) -> None:
        """Helper function to recursively check list comprehensions."""
        if not gens:
            self.visit(node.elt)
            return

        # Check the iterator expression in the current scope
        gen, *gens = gens
        self.visit(gen.iter_assign.value)
        assert isinstance(gen.iter, PlaceNode)

        # The rest is checked in a new nested scope so we can track which variables
        # are introduced and used inside the loop
        with self.new_scope() as inner_scope:
            # In particular, assign the iterator variable in the new scope
            self._check_assign_targets(gen.iter_assign.targets)
            self.visit(gen.hasnext_assign)
            self.visit(gen.next_assign)

            # `if` guards are generally not allowed when we're iterating over linear
            # variables. The only exception is if all linear variables are already
            # consumed by the first guard
            if gen.ifs:
                first_if, *other_ifs = gen.ifs
                # Check if there are linear iteration variables that have not been used
                # by the first guard
                self.visit(first_if)
                for place in self.scope.vars.values():
                    # The only exception is the iterator variable since we make sure
                    # that it is carried through each iteration during Hugr generation
                    if place == gen.iter.place:
                        continue
                    for leaf in leaf_places(place):
                        x = leaf.id
                        if not self.scope.used(x) and place.ty.linear:
                            raise GuppyTypeError(
                                f"{place.describe} with linear type `{place.ty}` is "
                                "not used on all control-flow paths of the list "
                                "comprehension",
                                place.defined_at,
                            )
                for expr in other_ifs:
                    self.visit(expr)

            # Recursively check the remaining generators
            self._check_comprehension(node, gens)

            # Check the iter finalizer so we record a final use of the iterator
            self.visit(gen.iterend)

            # We have to make sure that all linear variables that were introduced in the
            # inner scope have been used
            for place in inner_scope.vars.values():
                for leaf in leaf_places(place):
                    x = leaf.id
                    if leaf.ty.linear and not inner_scope.used(x):
                        raise GuppyTypeError(
                            f"{leaf.describe} with linear type `{leaf.ty}` is not used",
                            leaf.defined_at,
                        )

            # On the other hand, we have to ensure that no linear places from the
            # outer scope have been used inside the comprehension (they would be used
            # multiple times since the comprehension body is executed repeatedly)
            for x, use in inner_scope.used_parent.items():
                place = inner_scope[x]
                if place.ty.linear:
                    raise GuppyTypeError(
                        f"{place.describe} with linear type `{place.ty}` would be used "
                        "multiple times when evaluating this comprehension",
                        use,
                    )


def leaf_places(place: Place) -> Iterator[Place]:
    """Returns all leaf descendant projections of a place."""
    stack = [place]
    while stack:
        place = stack.pop()
        if isinstance(place.ty, StructType):
            stack += [
                FieldAccess(place, field, place.defined_at) for field in place.ty.fields
            ]
        else:
            yield place


def is_inout_var(place: Place) -> TypeGuard[Variable]:
    """Checks whether a place is an @inout variable."""
    return isinstance(place, Variable) and InputFlags.Inout in place.flags


def check_cfg_linearity(
    cfg: "CheckedCFG[Variable]", globals: Globals
) -> "CheckedCFG[Place]":
    """Checks whether a CFG satisfies the linearity requirements.

    Raises a user-error if linearity violations are found.

    Returns a new CFG with refined basic block signatures in terms of *places* rather
    than just variables.
    """
    bb_checker = BBLinearityChecker()
    scopes: dict[BB, Scope] = {
        bb: bb_checker.check(bb, is_entry=bb == cfg.entry_bb, globals=globals)
        for bb in cfg.bbs
    }

    # Check that @inout vars are not being shadowed. This would also be caught by
    # the dataflow analysis below, however we can give nicer error messages here.
    for bb, scope in scopes.items():
        if bb == cfg.entry_bb:
            # Arguments are assigned in the entry BB, so would yield a false positive
            # in the check below. Shadowing in the entry BB will be caught by the check
            # in `_check_assign_targets`.
            continue
        entry_scope = scopes[cfg.entry_bb]
        for x, place in scope.vars.items():
            if x in entry_scope:
                entry_place = entry_scope[x]
                if is_inout_var(entry_place):
                    raise GuppyError(
                        f"Assignment shadows argument `{entry_place}` annotated as "
                        "`@inout`. Consider assigning to a different name.",
                        place.defined_at,
                    )

    # Mark the @inout variables as implicitly used in the exit BB
    exit_scope = scopes[cfg.exit_bb]
    for var in cfg.entry_bb.sig.input_row:
        if InputFlags.Inout in var.flags:
            for leaf in leaf_places(var):
                exit_scope.use(leaf.id, InoutReturnSentinel(var=var))

    # Run liveness analysis
    stats = {bb: scope.stats() for bb, scope in scopes.items()}
    live_before = LivenessAnalysis(stats).run(cfg.bbs)

    # Construct a CFG that tracks places instead of just variables
    result_cfg: CheckedCFG[Place] = CheckedCFG(cfg.input_tys, cfg.output_ty)
    checked: dict[BB, CheckedBB[Place]] = {}

    for bb, scope in scopes.items():
        live_before_bb = live_before[bb]

        # We have to check that used linear variables are not being outputted
        for succ in bb.successors:
            live = live_before[succ]
            for x, use_bb in live.items():
                use_scope = scopes[use_bb]
                place = use_scope[x]
                if place.ty.linear and (prev_use := scope.used(x)):
                    use = use_scope.used_parent[x]
                    # Special case if this is a use arising from the implicit returning
                    # of an @inout argument
                    if isinstance(use, InoutReturnSentinel):
                        assert isinstance(use.var, Variable)
                        assert InputFlags.Inout in use.var.flags
                        raise GuppyError(
                            f"Argument `{use.var}` annotated as `@inout` cannot be "
                            f"returned to the caller since `{place}` is used at {{0}}. "
                            f"Consider writing a value back into `{place}` before "
                            "returning.",
                            use.var.defined_at,
                            [prev_use],
                        )
                    raise GuppyError(
                        f"{place.describe} with linear type `{place.ty}` was "
                        "already used (at {0})",
                        use,
                        [prev_use],
                    )

            # On the other hand, unused linear variables *must* be outputted
            for place in scope.values():
                for leaf in leaf_places(place):
                    x = leaf.id
                    # Some values are just in scope because the type checker determined
                    # them as live in the first (less precises) dataflow analysis. It
                    # might be the case that x is actually not live when considering
                    # the second, more fine-grained, analysis based on places.
                    if x not in live_before_bb and x not in scope.vars:
                        continue
                    used_later = x in live
                    if leaf.ty.linear and not scope.used(x) and not used_later:
                        # TODO: This should be "Variable x with linear type ty is not
                        #  used in {bb}". But for this we need a way to associate BBs
                        #  with source locations.
                        raise GuppyError(
                            f"{leaf.describe} with linear type `{leaf.ty}` is "
                            "not used on all control-flow paths",
                            # Re-lookup defined_at in scope because we might have a
                            # more precise location
                            scope[x].defined_at,
                        )

        def live_places_row(bb: BB, original_row: Row[Variable]) -> Row[Place]:
            """Construct a row of all places that are live at the start of a given BB.

            The only exception are input and exit BBs whose signature should not be
            split up into places but instead keep the original variable signature.
            """
            if bb in (cfg.entry_bb, cfg.exit_bb):
                return original_row
            # N.B. we can ignore lint B023. The use of loop variable `scope` below is
            # safe since we don't call this function outside the loop.
            return [scope[x] for x in live_before[bb]]  # noqa: B023

        assert isinstance(bb, CheckedBB)
        sig = Signature(
            input_row=live_places_row(bb, bb.sig.input_row),
            output_rows=[
                live_places_row(succ, output_row)
                for succ, output_row in zip(
                    bb.successors, bb.sig.output_rows, strict=True
                )
            ],
        )
        checked[bb] = CheckedBB(
            bb.idx, result_cfg, bb.statements, branch_pred=bb.branch_pred, sig=sig
        )

    # Fill in missing fields of the result CFG
    result_cfg.bbs = list(checked.values())
    result_cfg.entry_bb = checked[cfg.entry_bb]
    result_cfg.exit_bb = checked[cfg.exit_bb]
    result_cfg.live_before = {checked[bb]: cfg.live_before[bb] for bb in cfg.bbs}
    result_cfg.ass_before = {checked[bb]: cfg.ass_before[bb] for bb in cfg.bbs}
    result_cfg.maybe_ass_before = {
        checked[bb]: cfg.maybe_ass_before[bb] for bb in cfg.bbs
    }
    for bb in cfg.bbs:
        checked[bb].predecessors = [checked[pred] for pred in bb.predecessors]
        checked[bb].successors = [checked[succ] for succ in bb.successors]
    return result_cfg
