from guppylang import guppy
from guppylang.std.builtins import nat


@guppy
def main[n: nat](b: bool) -> nat:
    if b:
        n = nat(42)
    return n


main.compile()
