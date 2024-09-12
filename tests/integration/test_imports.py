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


def test_import_implicit(validate):
    from tests.integration.modules.implicit_mod import foo

    module = GuppyModule("test")
    module.load(foo)

    @guppy(module)
    def test(x: int) -> int:
        return foo(x)

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


def test_qualified(validate):
    import tests.integration.modules.mod_a as mod_a
    import tests.integration.modules.mod_b as mod_b

    module = GuppyModule("test")
    module.load(mod_a, mod_b)

    @guppy(module)
    def test(x: int, y: bool) -> tuple[int, bool]:
        return mod_a.f(x), mod_b.f(y)

    validate(module.compile())


def test_qualified_types(validate):
    import tests.integration.modules.mod_a as mod_a
    import tests.integration.modules.mod_b as mod_b

    module = GuppyModule("test")
    module.load(mod_a, mod_b)

    @guppy(module)
    def test(x: mod_a.MyType, y: mod_b.MyType) -> tuple[mod_a.MyType, mod_b.MyType]:
        return -x, +y

    validate(module.compile())


def test_qualified_implicit(validate):
    import tests.integration.modules.implicit_mod as implicit_mod

    module = GuppyModule("test")
    module.load(implicit_mod)

    @guppy(module)
    def test(x: int) -> int:
        return implicit_mod.foo(x)

    validate(module.compile())


def test_private_func(validate):
    # First, define a module with a public function
    # that calls an internal one
    internal_module = GuppyModule("test_internal")

    @guppy(internal_module)
    def _internal(x: int) -> int:
        return x

    @guppy(internal_module)
    def g(x: int) -> int:
        return _internal(x)

    # The test module
    module = GuppyModule("test")
    module.load_all(internal_module)

    @guppy(module)
    def f(x: int) -> int:
        return g(x)

    hugr = module.compile()
    validate(hugr)
