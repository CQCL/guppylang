from guppylang.decorator import guppy
from guppylang.prelude.builtins import linst
from guppylang.module import GuppyModule

module = GuppyModule("test")


@guppy(module)
def main(x: linst[int]) -> linst[int]:
    return x


module.compile()
