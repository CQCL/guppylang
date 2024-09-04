from guppylang.decorator import guppy
from guppylang.module import GuppyModule

import tests.error.import_errors.lib as lib

module = GuppyModule("test")
module.load(lib)


@guppy(module)
def main(x: int) -> int:
    return lib.bar(x)


module.compile()
