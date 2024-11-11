from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("test")

X = guppy.type_var("X", module=module)


class Generic:
    """Fake Generic type that doesn't check for type var uniqueness."""
    def __class_getitem__(cls, item):
        return cls


@guppy.struct(module)
class MyStruct(Generic[X, X]):
    x: int


module.compile()
