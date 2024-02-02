from guppylang import GuppyModule, guppy
from tests.integration.modules.mod_a import mod_a, MyType
from tests.integration.modules.mod_b import mod_b

module = GuppyModule("test")
module.import_(mod_a, "MyType")
module.import_(mod_b, "MyType", alias="MyType2")


@guppy(module)
def foo(x: MyType) -> MyType:
    return +x


module.compile()
