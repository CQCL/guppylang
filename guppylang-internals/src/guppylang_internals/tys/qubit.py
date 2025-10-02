import functools
from typing import cast

from guppylang_internals.definition.ty import TypeDef
from guppylang_internals.tys.ty import Type


@functools.cache
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
