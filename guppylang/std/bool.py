"""Operations on booleans."""

# mypy: disable-error-code="empty-body, misc, override, valid-type, no-untyped-def"

from __future__ import annotations

from typing import no_type_check

from guppylang.decorator import guppy
from guppylang.definition.custom import NoopCompiler
from guppylang.std._internal.checker import DunderChecker
from guppylang.std._internal.util import bool_logic_op
from guppylang.std.num import nat
from guppylang.tys.builtin import bool_type_def


@guppy.extend_type(bool_type_def)
class bool:
    """Booleans representing truth values.

    The bool type has exactly two constant instances: ``True`` and ``False``.

    The bool constructor takes a single argument and converts it to ``True`` or
    ``False`` using the standard truth testing procedure.
    """

    @guppy.hugr_op(bool_logic_op("and"))
    def __and__(self: bool, other: bool) -> bool: ...

    @guppy.custom(NoopCompiler())
    def __bool__(self: bool) -> bool: ...

    @guppy.hugr_op(bool_logic_op("eq"))
    def __eq__(self: bool, other: bool) -> bool: ...

    @guppy
    @no_type_check
    def __ne__(self: bool, other: bool) -> bool:
        return not self == other

    @guppy
    @no_type_check
    def __int__(self: bool) -> int:
        return 1 if self else 0

    @guppy
    @no_type_check
    def __nat__(self: bool) -> nat:
        # TODO: Type information doesn't flow through the `if` expression, so we
        #  have to insert the `nat` coercions by hand.
        #  See https://github.com/CQCL/guppylang/issues/707
        return nat(1) if self else nat(0)

    @guppy.custom(checker=DunderChecker("__bool__"), higher_order_value=False)
    def __new__(x): ...

    @guppy.hugr_op(bool_logic_op("or"))
    def __or__(self: bool, other: bool) -> bool: ...

    @guppy.hugr_op(bool_logic_op("xor"))
    def __xor__(self: bool, other: bool) -> bool: ...
