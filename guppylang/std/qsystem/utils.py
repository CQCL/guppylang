from typing import no_type_check

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std._internal.compiler.quantum import QSYSTEM_UTILS_EXTENSION
from guppylang.std._internal.util import external_op

qsystem_utils = GuppyModule("qsystem.utils")


@guppy.hugr_op(
    external_op("GetCurrentShot", [], ext=QSYSTEM_UTILS_EXTENSION), module=qsystem_utils
)
@no_type_check
def get_current_shot() -> int: ...
