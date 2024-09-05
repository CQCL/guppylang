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

    default_module = guppy.get_module()

    assert not module.contains("a")
    assert module.contains("b")
    assert not module.contains("c")

    assert default_module.contains("a")
    assert not default_module.contains("b")
    assert default_module.contains("c")


def test_nested():
    def make_module() -> GuppyModule:
        @guppy
        def a() -> None:
            pass

        return guppy.get_module()

    module_a = make_module()
    module_b = make_module()

    assert module_a.contains("a")
    assert module_b.contains("a")
