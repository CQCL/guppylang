from typing import no_type_check

from guppylang.decorator import guppy
from guppylang.std._internal.compiler.tket_exts import QSYSTEM_UTILS_EXTENSION
from guppylang.std._internal.util import external_op


@guppy.hugr_op(external_op("GetCurrentShot", [], ext=QSYSTEM_UTILS_EXTENSION))
@no_type_check
def get_current_shot() -> int:
    """Get the current shot number."""
