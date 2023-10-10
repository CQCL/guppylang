from guppy.compiler import guppy


def test_basic(validate):
    x = 42

    @guppy
    def foo() -> int:
        return py(x + 1)

    validate(foo)


def test_builtin(validate):

    @guppy
    def foo() -> int:
        return py(len({"a": 1337, "b": None}))

    validate(foo)


def test_if(validate):
    b = True

    @guppy
    def foo() -> int:
        if py(b or 1 > 6):
            return 0
        return 1

    validate(foo)


def test_redeclare_after(validate):
    x = 1

    @guppy
    def foo() -> int:
        return py(x)

    x = False

    validate(foo)


def test_tuple(validate):
    @guppy
    def foo() -> int:
        x, y = py((1, 2))
        return x

    validate(foo)
