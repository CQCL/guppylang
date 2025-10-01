import functools
from typing import Any, cast

from guppylang_internals.definition.ty import TypeDef
from guppylang_internals.tys.arg import TypeArg
from guppylang_internals.tys.common import Visitor
from guppylang_internals.tys.ty import OpaqueType, Type


def qubit_ty() -> Type:
    """Returns the qubit type. Beware that this function imports guppylang definitions,
    so, if called before the definitions are registered,
    it might result in circular imports.
    """
    from guppylang.defs import GuppyDefinition
    from guppylang.std.quantum import qubit

    assert isinstance(qubit, GuppyDefinition)
    qubit_ty = cast(TypeDef, qubit.wrapped).check_instantiate([])
    return qubit_ty


def is_qubit_ty(ty: Type) -> bool:
    """Checks if the given type is the qubit type.
    This function results in circular imports if called
    before qubit types are registered.
    """
    return ty == qubit_ty()


class QubitFinder(Visitor):
    """Type visitor that checks if a type contains the qubit type."""

    class FoundFlag(Exception):
        pass

    @functools.singledispatchmethod
    def visit(self, ty: Any, /) -> bool:  # type: ignore[override]
        return False

    @visit.register
    def _visit_OpaqueType(self, ty: OpaqueType) -> bool:
        if is_qubit_ty(ty):
            raise self.FoundFlag
        return False

    @visit.register
    def _visit_TypeArg(self, arg: TypeArg) -> bool:
        arg.ty.visit(self)
        return True


def contain_qubit_ty(ty: Type) -> bool:
    """Checks if the given type contains the qubit type."""
    finder = QubitFinder()
    try:
        ty.visit(finder)
    except QubitFinder.FoundFlag:
        return True
    else:
        return False
