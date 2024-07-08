"""Linearity checking

Linearity checking across control-flow is done by the `CFGChecker`.
"""

import ast
from collections import deque
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING

from guppylang.ast_util import AstNode, find_nodes, get_type
from guppylang.cfg.analysis import LivenessAnalysis
from guppylang.cfg.bb import BB, VariableStats
from guppylang.checker.core import (
    FieldAccess,
    Locals,
    Place,
    PlaceId,
    Variable,
)
from guppylang.error import GuppyError, GuppyTypeError
from guppylang.nodes import (
    CheckedNestedFunctionDef,
    DesugaredGenerator,
    DesugaredListComp,
    FieldAccessAndDrop,
    PlaceNode,
)
from guppylang.tys.ty import StructType

if TYPE_CHECKING:
    from guppylang.checker.cfg_checker import CheckedBB, CheckedCFG


class Scope(Locals[PlaceId, Place]):
    """Scoped collection of assigned places indexed by their id.

    Keeps track of which places have already been used.
    """

    parent_scope: "Scope | None"
    used_local: dict[str, ast.Name]
    used_parent: dict[str, ast.Name]

    def __init__(self, assigned: Iterable[Variable], parent: "Scope | None" = None):
        self.used_local = {}
        self.used_parent = {}
        super().__init__({var.name: var for var in assigned}, parent)

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


class BBLinearityChecker(ast.NodeVisitor):
    """AST visitor that checks linearity for a single basic block."""

    scope: Scope

    def check(self, bb: "CheckedBB") -> Scope:
        self.scope = Scope(bb.sig.input_row)
        for stmt in bb.statements:
            self.visit(stmt)
        if bb.branch_pred:
            self.visit(bb.branch_pred)
        return self.scope

    @contextmanager
    def new_scope(self) -> Generator[Scope, None, None]:
        scope, new_scope = self.scope, Scope({}, self.scope)
        self.scope = new_scope
        yield new_scope
        self.scope = scope

    def visit_PlaceNode(self, node: PlaceNode) -> None:
        place = node.place
        x = place.id
        if (use := self.scope.used(x)) and place.ty.linear:
            raise GuppyError(
                f"{place.describe} with linear type `{place.ty}` was already used "
                "(at {0})",
                node,
                [use],
            )
        self.scope.use(x, node)

    def visit_Assign(self, node: ast.Assign) -> None:
        self.visit(node.value)
        self._check_assign_targets(node.targets)

    def visit_Expr(self, node: ast.Expr) -> None:
        # An expression statement where the return value is discarded
        self.visit(node.value)
        ty = get_type(node.value)
        if ty.linear:
            raise GuppyTypeError(f"Value with linear type `{ty}` is not used", node)

    def visit_DesugaredListComp(self, node: DesugaredListComp) -> None:
        self._check_comprehension(node, node.generators)

    def _check_assign_targets(self, targets: list[ast.expr]) -> None:
        """Helper function to check assignments."""
        # We're not allowed to override an unused linear place
        [target] = targets
        for tgt in find_nodes(lambda n: isinstance(n, PlaceNode), target):
            assert isinstance(tgt, PlaceNode)
            x = tgt.place.id
            if x in self.scope and not self.scope.used(x):
                place = self.scope[x]
                if place.ty.linear:
                    raise GuppyError(
                        f"{place.describe} with linear type `{place.ty}` is not "
                        "used",
                        place.defined_at,
                    )
            self.scope.assign(tgt.place)

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
                for x, place in self.scope.vars.items():
                    # The only exception is the iterator variable since we make sure
                    # that it is carried through each iteration during Hugr generation
                    if place == gen.iter.place:
                        continue
                    if not self.scope.used(x) and place.ty.linear:
                        raise GuppyTypeError(
                            f"{place.describe} with linear type `{place.ty}` is not "
                            "used on all control-flow paths of the list comprehension",
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
            for x, place in inner_scope.vars.items():
                if place.ty.linear and not inner_scope.used(x):
                    raise GuppyTypeError(
                        f"{place.describe} with linear type `{place.ty}` is not used",
                        place.defined_at,
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


def check_cfg_linearity(cfg: "CheckedCFG") -> None:
    """Checks whether a CFG satisfies the linearity requirements.

    Raises a user-error if linearity violations are found.
    """
    bb_checker = BBLinearityChecker()
    for bb in cfg.bbs:
        scope = bb_checker.check(bb)

        # We have to check that used linear variables are not being outputted
        for succ in bb.successors:
            live = cfg.live_before[succ]
            for x, use_bb in live.items():
                if x in scope:
                    var = scope[x]
                    if var.ty.linear and (use := scope.used(x)):
                        raise GuppyError(
                            f"Variable `{x}` with linear type `{var.ty}` was "
                            "already used (at {0})",
                            use_bb.vars.used[x],
                            [use],
                        )

            # On the other hand, unused linear variables *must* be outputted
            for x, var in scope.vars.items():
                used_later = x in cfg.live_before[succ]
                if var.ty.linear and not scope.used(x) and not used_later:
                    # TODO: This should be "Variable x with linear type ty is not
                    #  used in {bb}". But for this we need a way to associate BBs with
                    #  source locations.
                    raise GuppyError(
                        f"Variable `{x}` with linear type `{var.ty}` is "
                        "not used on all control-flow paths",
                        var.defined_at,
                    )
