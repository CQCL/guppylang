from typing import no_type_check
from guppylang.decorator import guppy
from guppylang.std.builtins import barrier
from guppylang.std.quantum import qubit


@guppy
@no_type_check
def main() -> None:
   barrier(qubit())


guppy.compile(main)
