from guppylang import GuppyModule, guppy


def test_import_func(validate):
    from tests.integration.modules.mod_a import f, g

    module = GuppyModule("test")
    module.load(f, g)

    @guppy(module)
    def test(x: int) -> int:
        return f(x) + g()

    validate(module.compile())


def test_import_type(validate):
    from tests.integration.modules.mod_a import MyType

    module = GuppyModule("test")
    module.load(MyType)

    @guppy(module)
    def test(x: MyType) -> MyType:
        # Check that we've correctly imported the __neg__ method
        return -x

    validate(module.compile())


def test_func_alias(validate):
    from tests.integration.modules.mod_a import f as g

    module = GuppyModule("test")
    module.load(g=g)

    @guppy(module)
    def test(x: int) -> int:
        return g(x)

    validate(module.compile())


def test_type_alias(validate):
    from tests.integration.modules.mod_a import MyType

    module = GuppyModule("test")
    module.load(MyType_Alias=MyType)

    @guppy(module)
    def test(x: "MyType_Alias") -> "MyType_Alias":
        # Check that we still have the __neg__ method
        return -x

    validate(module.compile())


def test_conflict_alias(validate):
    from tests.integration.modules.mod_a import f
    from tests.integration.modules.mod_b import f as f_b

    module = GuppyModule("test")
    module.load(f, f_b=f_b)

    @guppy(module)
    def test(x: int, y: bool) -> tuple[int, bool]:
        return f(x), f_b(y)

    validate(module.compile())


def test_conflict_alias_type(validate):
    from tests.integration.modules.mod_a import MyType
    from tests.integration.modules.mod_b import MyType as MyTypeB

    module = GuppyModule("test")
    module.load(MyType, MyTypeB=MyTypeB)

    @guppy(module)
    def test(x: MyType, y: MyTypeB) -> tuple[MyType, MyTypeB]:
        return -x, +y

    validate(module.compile())


def test_type_transitive(validate):
    from tests.integration.modules.mod_c import g

    module = GuppyModule("test")
    module.load(g)  # `g` returns a type that was defined in `mod_a`

    @guppy(module)
    def test() -> int:
        x = g()  # Type of x was defined in `mod_a`
        return int(-x)  # Call method that was defined in `mod_a`

    validate(module.compile())


def test_type_transitive_conflict(validate):
    from tests.integration.modules.mod_b import MyType
    from tests.integration.modules.mod_c import g

    module = GuppyModule("test")
    module.load(MyType, g)

    @guppy(module)
    def test(ty_b: MyType) -> MyType:
        ty_a = g()  # g returns a type with the same name `MyType`
        return +ty_b

    validate(module.compile())


def test_func_transitive(validate):
    from tests.integration.modules.mod_c import h

    module = GuppyModule("test")
    module.load(h)  # `h` calls a function that was defined in `mod_a`

    @guppy(module)
    def test(x: int) -> int:
        return h(x)

    validate(module.compile())
