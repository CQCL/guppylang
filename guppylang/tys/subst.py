import functools
from collections.abc import Sequence, Iterator
from contextlib import contextmanager
from typing import Any

from guppylang.error import InternalGuppyError
from guppylang.tys.arg import Argument, TypeArg
from guppylang.tys.ty import Type, ExistentialTypeVar, BoundTypeVar, FunctionType
from guppylang.tys.common import Transformer
from guppylang.tys.const import ExistentialConstVar, BoundConstVar
from guppylang.tys.var import ExistentialVar


Subst = dict[ExistentialVar, Type]  # TODO: `GuppyType | Const` or `Argument` ??
Inst = Sequence[Argument]


class Substituter(Transformer):
    """Type transformer that applies a substitution of existential variables."""

    def __init__(self, subst: Subst) -> None:
        self.subst = subst

    @functools.singledispatchmethod
    def transform(self, ty: Any) -> Any | None:   # type: ignore[override]
        return None

    @transform.register
    def _transform_ExistentialTypeVar(self, ty: ExistentialTypeVar) -> Type | None:
        return self.subst.get(ty, None)

    @transform.register
    def _transform_ExistentialConstVar(self, ty: ExistentialConstVar) -> Type | None:
        raise NotImplementedError


class Instantiator(Transformer):
    """Type transformer that instantiates bound variables."""

    def __init__(self, inst: Inst) -> None:
        self.inst = inst

    @functools.singledispatchmethod
    def transform(self, ty: Any) -> Any | None:  # type: ignore[override]
        return None

    @transform.register
    def _transform_BoundTypeVar(self, ty: BoundTypeVar) -> Type | None:
        # Instantiate if type for the index is available
        if ty.idx < len(self.inst):
            arg = self.inst[ty.idx]
            assert isinstance(arg, TypeArg)
            return arg.ty

        # Otherwise, lower the de Bruijn index
        return BoundTypeVar(ty.display_name, ty.idx - len(self.inst), ty.linear)

    @transform.register
    def _transform_BoundConstVar(self, ty: BoundConstVar) -> Type | None:
        raise NotImplementedError

    @transform.register
    def _transform_FunctionType(self, ty: FunctionType) -> Type | None:
        if ty.parametrized:
            raise InternalGuppyError("Tried to instantiate under binder")
        return None

