from guppylang.decorator import guppy


def build():
    @guppy.struct
    class Foo:
        x: "blah"

    return Foo


guppy.compile(build())
