from guppylang.decorator import custom_guppy_decorator, guppy


@custom_guppy_decorator
def my_guppy(f):
    return guppy(f)


def test_custom_decorator(validate):
    def make():
        @my_guppy
        def foooo() -> int:
            return 1 + bar()

        return foooo

    foo = make()

    @guppy
    def bar() -> int:
        return 2 + foo()

    @my_guppy
    def main() -> int:
        return foo() + bar() + main()

    validate(guppy.compile(main))
