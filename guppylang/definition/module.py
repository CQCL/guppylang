from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from guppylang.definition.common import CompiledDef

if TYPE_CHECKING:
    from guppylang.checker.core import Globals


@dataclass(frozen=True)
class ModuleDef(CompiledDef):
    """A module definition.

    Note that this definition is separate from the `GuppyModule` class and only serves
    as a pointer to be stored in the globals.

    In the future we could consider unifying this with `GuppyModule`.
    """

    globals: "Globals"

    description: str = field(default="module", init=False)
