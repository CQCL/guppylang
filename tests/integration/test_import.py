from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from tests.integration.modules.mod_a import mod_a, MyType, f, g
from tests.integration.modules.mod_b import mod_b
from tests.integration.modules.mod_c import mod_c


def test_import_func(validate):
    module = GuppyModule("test")
    module.import_(mod_a, "f")
    module.import_(mod_a, "g")

    @guppy(module)
    def test(x: int) -> int:
        return f(x) + g()

    validate(module.compile())


def test_import_type(validate):
    module = GuppyModule("test")
    module.import_(mod_a, "MyType")

    @guppy(module)
    def test(x: MyType) -> MyType:
        return -x

    validate(module.compile())


def test_func_alias(validate):
    module = GuppyModule("test")
    module.import_(mod_a, "f", alias="g")

    @guppy(module)
    def test(x: int) -> int:
        return g(x)

    validate(module.compile())


def test_type_alias(validate):
    module = GuppyModule("test")
    module.import_(mod_a, "MyType", alias="MyType_Alias")

    @guppy(module)
    def test(x: "MyType_Alias") -> "MyType_Alias":
        return -x

    validate(module.compile())


def test_conflict_alias(validate):
    module = GuppyModule("test")
    module.import_(mod_a, "f")
    module.import_(mod_b, "f", alias="f_b")

    @guppy(module)
    def test(x: int, y: bool) -> tuple[int, bool]:
        return f(x), f_b(y)

    validate(module.compile())


def test_conflict_alias_type(validate):
    module = GuppyModule("test")
    module.import_(mod_a, "MyType")
    module.import_(mod_b, "MyType", alias="MyTypeB")

    @guppy(module)
    def test(x: MyType, y: "MyTypeB") -> tuple[MyType, "MyTypeB"]:
        return -x, +y

    validate(module.compile())


def test_type_transitive(validate):
    module = GuppyModule("test")
    module.import_(mod_c, "g")  # `g` returns a type that was defined in `mod_a`

    @guppy(module)
    def test() -> int:
        x = g()
        return int(-x)  # Use instance method that was defined in `mod_a`

    validate(module.compile())


def test_type_transitive_conflict(validate):
    module = GuppyModule("test")
    module.import_(mod_b, "MyType")
    module.import_(mod_c, "g")

    @guppy(module)
    def test(ty_b: MyType) -> MyType:
        ty_a = g()
        return +ty_b

    validate(module.compile())


from guppylang.prelude.quantum import Qubit as MyQubit, h as my_h


def test_implicit_import(validate):
    @guppy
    def test(q: MyQubit) -> MyQubit:
        return my_h(q)

    validate(guppy.compile_module())
