import validator
from guppy.compiler import GuppyModule
from guppy.visualise import render_hugr

module = GuppyModule("test")


@module
def fac(x: int) -> int:
    acc = 1
    while x > 0:
        acc *= x
        x -= 1
    return acc


if __name__ == "__main__":
    hugr = module.compile(True)

    # Render Hugr for debugging into `hugr.svg`
    render_hugr(hugr, "hugr")

    validator.nest_cfg(hugr.serialize())
