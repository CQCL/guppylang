import ast

from guppylang.cfg.bb import BBStatement
from guppylang.checker.cfg_checker import CheckedBB, CheckedCFG
from guppylang.checker.core import (
    Globals,
    Place,
    PlaceId,
    Variable,
)

from guppylang.nodes import (
    CopyNode,
    FieldAccessAndDrop,
    GlobalCall,
    LocalCall,
    PartialApply,
    PlaceNode,
    SubscriptAccessAndDrop,
    TensorCall,
)

from guppylang.checker.linearity_checker import Scope, leaf_places, contains_subscript


class ProgramDependencies:
    mapping: dict[BBStatement, set[PlaceId]]

    def __init__(self, mapping: dict[BBStatement, set[PlaceId]] = None):
        if mapping is None:
            mapping = {}
        self.mapping = mapping

    def add_stmt(self, stmt: BBStatement) -> None:
        self.mapping[stmt] = set()

    def add_dep(self, stmt: BBStatement, place: PlaceId) -> None:
        self.mapping[stmt].add(place)

    def add_deps(self, stmt: BBStatement, places: set[PlaceId]) -> None:
        self.mapping[stmt].update(places)


class BBDependencyAnalyser(ast.NodeVisitor):
    """AST visitor that computes dependencies for a single basic block."""

    func_inputs: dict[PlaceId, Variable]
    globals: Globals

    all_deps: ProgramDependencies

    def check(
        self,
        bb: "CheckedBB[Place]",
        globals: Globals,
    ) -> Scope:
        self.globals = globals

        self.all_deps = ProgramDependencies()

        for stmt in bb.statements:
            self.all_deps.add_stmt(stmt)
            self.all_deps.add_deps(stmt, self.visit(stmt))
        if bb.branch_pred:
            self.all_deps.add_stmt(bb.branch_pred)
            self.all_deps.add_deps(bb.branch_pred, self.visit(bb.branch_pred))

    # Probably non-exhaustive list of AST nodes that can contain places.
    def visit_CopyNode(self, node: CopyNode) -> set[PlaceId]:
        return set(node.value.place.id)

    def visit_PlaceNode(self, node: PlaceNode) -> set[PlaceId]:
        deps = set()
        if subscript := contains_subscript(node.place):
            self.visit(subscript.item_expr)
            deps.add(subscript.item.id)
            deps.add(subscript.parent.id)
        else:
            for place in leaf_places(node.place):
                deps.add(place.id)
        return deps

    def visit_Assign(self, node: ast.Assign) -> set[PlaceId]:
        deps = self.visit(node.value)
        for target in node.targets:
            deps.update(self.visit(target))
        return deps

    def visit_Return(self, node: ast.Return) -> set[PlaceId]:
        if node.value:
            return self.visit(node.value)
        return set()

    def visit_GlobalCall(self, node: GlobalCall) -> set[PlaceId]:
        deps = set()
        for arg in node.args:
            deps.update(self.visit(arg))
        return deps

    def visit_LocalCall(self, node: LocalCall) -> set[PlaceId]:
        deps = set()
        for arg in node.args:
            deps.update(self.visit(arg))
        return deps

    def visit_TensorCall(self, node: TensorCall) -> set[PlaceId]:
        deps = set()
        for arg in node.args:
            deps.update(self.visit(arg))
        return deps

    def visit_PartialApply(self, node: PartialApply) -> set[PlaceId]:
        deps = set()
        for arg in node.args:
            deps.update(self.visit(arg))
        return deps

    def visit_FieldAccessAndDrop(self, node: FieldAccessAndDrop) -> set[PlaceId]:
        return self.visit(node.value)

    def visit_SubscriptAccessAndDrop(
        self, node: SubscriptAccessAndDrop
    ) -> set[PlaceId]:
        return self.visit(node.item)

    def visit_Expr(self, node: ast.Expr) -> set[PlaceId]:
        return self.visit(node.value)

    def visit_BinOp(self, node: ast.BinOp) -> set[PlaceId]:
        deps = self.visit(node.left)
        deps.update(self.visit(node.right))
        return deps

    def visit_BoolOp(self, node: ast.BoolOp) -> set[PlaceId]:
        deps = set()
        for value in node.values:
            deps.update(self.visit(value))
        return deps

    def visit_Compare(self, node: ast.Compare) -> set[PlaceId]:
        deps = self.visit(node.left)
        for comparator in node.comparators:
            deps.update(self.visit(comparator))
        return deps

    def visit_Attribute(self, node: ast.Attribute) -> set[PlaceId]:
        return self.visit(node.value)

    def visit_Subscript(self, node: ast.Subscript) -> set[PlaceId]:
        deps = self.visit(node.value)
        deps.update(self.visit(node.slice))
        return deps

    def visit_List(self, node: ast.List) -> set[PlaceId]:
        deps = set()
        for elt in node.elts:
            deps.update(self.visit(elt))
        return deps

    def visit_Constant(self, _: ast.Constant) -> set[PlaceId]:
        return set()

    def visit_Name(self, node: ast.Name) -> set[PlaceId]:
        x = node.id
        if x in self.ctx.locals:
            var = self.ctx.locals[x]
            return {var.id}

    def visit_Call(self, node: ast.Call) -> set[PlaceId]:
        deps = set()
        for arg in node.args:
            deps.update(self.visit(arg))
        return deps


def compute_cfg_dependencies(
    cfg: CheckedCFG[Place], globals: Globals
) -> ProgramDependencies:
    # We ignore control flow for now since each dependency is just a local set of places.
    analyser = BBDependencyAnalyser()
    full_program_deps = ProgramDependencies(mapping={})

    for bb in cfg.bbs:
        analyser.check(bb, globals)
        full_program_deps.mapping.update(analyser.all_deps.mapping)

    return full_program_deps
