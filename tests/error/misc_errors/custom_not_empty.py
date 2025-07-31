from guppylang.decorator import custom_function


@custom_function()
def foo(x: int) -> int:
    return x


foo.compile()
