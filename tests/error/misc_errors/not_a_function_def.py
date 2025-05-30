from guppylang.decorator import guppy


f = lambda x: x
f = guppy(f)

guppy.compile(f)
