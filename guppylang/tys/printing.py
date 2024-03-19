from functools import singledispatchmethod
from typing import Any

from guppylang.error import InternalGuppyError
from guppylang.tys.arg import TypeArg, ConstArg
from guppylang.tys.common import Visitor
from guppylang.tys.param import TypeParam, ConstParam
from guppylang.tys.ty import GuppyType, BoundTypeVar, FunctionType, OpaqueType, \
    TupleType, SumType, NoneType
from guppylang.tys.var import Var, BoundVar, UniqueId, ExistentialVar


class TypePrinter:
    """Visitor that pretty prints types.

    Takes care of inserting minimal parentheses and renaming variables to make them
    unique.
    """

    # Store how often each user-picked display name is used to stand for different
    # variables
    used: dict[str, int]

    # Already chosen names for bound and existential variables
    bound_names: list[str]
    existential_names: dict[UniqueId, str]

    used_names: set[str]

    counter: dict[str, int]

    def __init__(self) -> None:
        self.used = {}
        self.bound_names = []
        self.existential_names = {}
        self.used_names = set()
        self.counter = {}

    def _fresh_name(self, display_name: str) -> str:
        if display_name not in self.used_names:
            self.counter[display_name] = 1
            self.used_names.add(display_name)
            return display_name

        # If the display name `T` has already been used, we start adding indices: `T`,
        # `T1`, `T2`, ...
        indexed = f"{display_name}{self.counter[display_name]}"

        # However, it could be the case that `T1` is a name that the user has already
        # chosen
        if indexed in self.used_names:
            return self._fresh_name(indexed)

        # Otherwise, we can use the indexed name
        self.counter[display_name] += 1
        self.used_names.add(indexed)
        return indexed

    def visit(self, ty: GuppyType) -> str:
        return self._visit(ty, False)

    @singledispatchmethod
    def _visit(self, ty: GuppyType, inside_row: bool) -> str:
        raise InternalGuppyError(f"Tried to pretty-print unknown type: {repr(ty)}")

    @_visit.register
    def _visit_BoundVar(self, var: BoundVar, inside_row: bool) -> str:
        return self.bound_names[var.idx]

    @_visit.register
    def _visit_ExistentialVar(self, var: ExistentialVar, inside_row: bool) -> str:
        if var.id not in self.existential_names:
            self.existential_names[var.id] = self._fresh_name(var.display_name)
        return f"?{self.existential_names[var.id]}"

    @_visit.register
    def _visit_FunctionType(self, ty: FunctionType, inside_row: bool) -> str:
        if ty.parametrized:
            for p in ty.params:
                self.bound_names.append(self._fresh_name(p.name))
        inputs = ", ".join([self._visit(inp, True) for inp in ty.inputs])
        if len(ty.inputs) != 1:
            inputs = f"({inputs})"
        output = self._visit(ty.output, True)
        if ty.parametrized:
            quantified = ", ".join([self._visit(param, False) for param in ty.params])
            del self.bound_names[:-len(ty.params)]
            return _wrap(f"forall {quantified}. {inputs} -> {output}", inside_row)
        return _wrap(f"{inputs} -> {output}", inside_row)

    @_visit.register
    def _visit_OpaqueType(self, ty: OpaqueType, inside_row: bool) -> str:
        if ty.args:
            args = ", ".join(self._visit(arg, True) for arg in ty.args)
            return f"{ty.defn.name}[{args}]"
        return ty.defn.name

    @_visit.register
    def _visit_TupleType(self, ty: TupleType, inside_row: bool) -> str:
        args = ", ".join(self._visit(arg, True) for arg in ty.args)
        return f"({args})"

    @_visit.register
    def _visit_SumType(self, ty: SumType, inside_row: bool) -> str:
        args = ", ".join(self._visit(arg, True) for arg in ty.args)
        return f"Sum[{args}]"

    @_visit.register
    def _visit_NoneType(self, ty: NoneType, inside_row: bool) -> str:
        return "None"

    @_visit.register
    def _visit_TypeParam(self, param: TypeParam, inside_row: bool) -> str:
        # TODO: Print linearity?
        return self.bound_names[-param.idx - 1]

    @_visit.register
    def _visit_ConstParam(self, param: ConstParam, inside_row: bool) -> str:
        kind = self._visit(param.ty, True)
        name = self.bound_names[-param.idx - 1]
        return f"{name}: {kind}"

    @_visit.register
    def _visit_TypeArg(self, arg: TypeArg, inside_row: bool) -> str:
        return self._visit(arg.ty, inside_row)

    @_visit.register
    def _visit_ConstArg(self, arg: ConstArg, inside_row: bool) -> str:
        return self._visit(arg.const, inside_row)


def _wrap(s: str, inside_row: bool) -> str:
    return f"({s})" if inside_row else s
