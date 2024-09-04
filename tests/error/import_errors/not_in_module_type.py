from guppylang.decorator import guppy
from guppylang.module import GuppyModule

import tests.error.import_errors.lib as lib

module = GuppyModule("test")
module.load(lib)


@guppy(module)
def main(x: "lib.MyType2") -> int:
    return 0


module.compile()
