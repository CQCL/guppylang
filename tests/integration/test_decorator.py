from guppylang.decorator import guppy
from guppylang.module import GuppyModule


def test_decorator():
    module = GuppyModule("test")

    @guppy
    def a() -> None:
        pass

    @guppy(module)
    def b() -> None:
        pass

    @guppy
    def c() -> None:
        pass

    default_module = guppy.take_module()

    assert not module.contains_function("a")
    assert module.contains_function("b")
    assert not module.contains_function("c")

    assert default_module.contains_function("a")
    assert not default_module.contains_function("b")
    assert default_module.contains_function("c")


def test_nested():
    def make_module() -> GuppyModule:
        @guppy
        def a() -> None:
            pass

        return guppy.take_module()

    module_a = make_module()
    module_b = make_module()

    assert module_a.contains_function("a")
    assert module_b.contains_function("a")
