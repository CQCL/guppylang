from guppylang.decorator import guppy

x = guppy.extern("x", ty="float[int]")

guppy.compile(x)
