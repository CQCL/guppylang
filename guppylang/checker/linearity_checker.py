"""Linearity checking

Linearity checking across control-flow is done by the `CFGChecker`.
"""

import ast
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING

from guppylang.ast_util import AstNode, find_nodes, get_type
from guppylang.cfg.analysis import LivenessAnalysis
from guppylang.cfg.bb import BB, VariableStats
from guppylang.checker.core import (
    FieldAccess,
    Globals,
    Locals,
    Place,
    PlaceId,
    Variable,
)
from guppylang.definition.value import CallableDef
from guppylang.error import GuppyError, GuppyTypeError
from guppylang.nodes import (
    CheckedNestedFunctionDef,
    DesugaredGenerator,
    DesugaredListComp,
    FieldAccessAndDrop,
    GlobalCall,
    LocalCall,
    PlaceNode,
    TensorCall,
)
from guppylang.tys.ty import FunctionType, InputFlags, StructType

if TYPE_CHECKING:
    from guppylang.checker.cfg_checker import CheckedBB, CheckedCFG


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

    def check(self, bb: "CheckedBB", is_entry: bool, globals: Globals) -> Scope:
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

    def visit_PlaceNode(self, node: PlaceNode) -> None:
        for place in leaf_places(node.place):
            x = place.id
            if use := self.scope.used(x):
                if isinstance(place, Variable) and InputFlags.Inout in place.flags:
                    raise GuppyError(
                        f"{place.describe} cannot be moved since it is annotated as "
                        "`@inout`",
                        node,
                        [use],
                    )
                if place.ty.linear:
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
        for arg in node.args:
            self.visit(arg)
        func = self.globals[node.def_id]
        assert isinstance(func, CallableDef)
        func_ty = func.ty.instantiate(node.type_args)
        self._reassign_inout_args(func_ty, node.args)

    def visit_LocalCall(self, node: LocalCall) -> None:
        for arg in node.args:
            self.visit(arg)
        func_ty = get_type(node.func)
        assert isinstance(func_ty, FunctionType)
        self._reassign_inout_args(func_ty, node.args)

    def visit_TensorCall(self, node: TensorCall) -> None:
        for arg in node.args:
            self.visit(arg)
        self._reassign_inout_args(node.tensor_ty, node.args)

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
            for tgt_place in leaf_places(tgt.place):
                x = tgt_place.id
                if x in self.scope and not self.scope.used(x):
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


def check_cfg_linearity(cfg: "CheckedCFG", globals: Globals) -> None:
    """Checks whether a CFG satisfies the linearity requirements.

    Raises a user-error if linearity violations are found.
    """
    bb_checker = BBLinearityChecker()
    scopes: dict[BB, Scope] = {
        bb: bb_checker.check(bb, is_entry=bb == cfg.entry_bb, globals=globals)
        for bb in cfg.bbs
    }

    # Run liveness analysis
    stats = {bb: scope.stats() for bb, scope in scopes.items()}
    live_before = LivenessAnalysis(stats).run(cfg.bbs)

    for bb, scope in scopes.items():
        # We have to check that used linear variables are not being outputted
        for succ in bb.successors:
            live = live_before[succ]
            for x, use_bb in live.items():
                use_scope = scopes[use_bb]
                place = use_scope[x]
                if place.ty.linear and (use := scope.used(x)):
                    raise GuppyError(
                        f"{place.describe} with linear type `{place.ty}` was "
                        "already used (at {0})",
                        use_scope.used_parent[x],
                        [use],
                    )

            # On the other hand, unused linear variables *must* be outputted
            for place in scope.vars.values():
                for leaf in leaf_places(place):
                    x = leaf.id
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
