from guppylang.decorator import guppy

x = guppy._extern("x", ty="float[int]")

guppy.compile(x)
