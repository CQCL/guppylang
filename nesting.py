import validator
from guppy.compiler import GuppyModule


module = GuppyModule("test")


@module
def fac(x: int) -> int:
    acc = 1
    while x > 0:
        acc *= x
        x -= 1
    return acc


if __name__ == "__main__":
    hugr = module.compile()
    validator.nest_cfg(hugr.serialize())
