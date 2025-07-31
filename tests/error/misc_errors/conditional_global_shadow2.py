from guppylang.decorator import guppy

x = guppy._extern("x", ty="str")

@guppy
def bad(b: bool) -> int:
    if b:
        x = 4
    return x

guppy.compile(bad)
