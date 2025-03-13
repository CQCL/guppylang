from collections.abc import Callable

import pytest

from hugr import tys as ht

from hugr import Wire

from guppylang.decorator import guppy
from guppylang.definition.custom import CustomCallCompiler
from guppylang.module import GuppyModule
from guppylang.std.builtins import array
from guppylang.std.quantum import qubit

import guppylang.std.quantum as quantum


def test_id(validate):
    module = GuppyModule("test")
    T = guppy.type_var("T", module=module)

    @guppy.declare(module)
    def foo(x: T) -> T: ...

    @guppy(module)
    def main(x: int) -> int:
        return foo(x)

    validate(module.compile())


def test_id_nested(validate):
    module = GuppyModule("test")
    T = guppy.type_var("T", module=module)

    @guppy.declare(module)
    def foo(x: T) -> T: ...

    @guppy(module)
    def main(x: int) -> int:
        return foo(foo(foo(x)))

    validate(module.compile())


def test_use_twice(validate):
    module = GuppyModule("test")
    T = guppy.type_var("T", module=module)

    @guppy.declare(module)
    def foo(x: T) -> T: ...

    @guppy(module)
    def main(x: int, y: bool) -> None:
        foo(x)
        foo(y)

    validate(module.compile())


def test_define_twice(validate):
    module = GuppyModule("test")
    T = guppy.type_var("T", module=module)

    @guppy.declare(module)
    def foo(x: T) -> T: ...

    @guppy.declare(module)
    def bar(x: T) -> T:  # Reuse same type var!
        ...

    @guppy(module)
    def main(x: bool, y: float) -> None:
        foo(x)
        foo(y)

    validate(module.compile())


def test_return_tuple_implicit(validate):
    module = GuppyModule("test")
    T = guppy.type_var("T", module=module)

    @guppy.declare(module)
    def foo(x: T) -> T: ...

    @guppy(module)
    def main(x: int) -> tuple[int, int]:
        return foo((x, 0))

    validate(module.compile())


def test_same_args(validate):
    module = GuppyModule("test")
    T = guppy.type_var("T", module=module)

    @guppy.declare(module)
    def foo(x: T, y: T) -> None: ...

    @guppy(module)
    def main(x: int) -> None:
        foo(x, 42)

    validate(module.compile())


def test_different_args(validate):
    module = GuppyModule("test")
    S = guppy.type_var("S", module=module)
    T = guppy.type_var("T", module=module)

    @guppy.declare(module)
    def foo(x: S, y: T, z: tuple[S, T]) -> T: ...

    @guppy(module)
    def main(x: int, y: float) -> float:
        return foo(x, y, (x, y)) + foo(y, 42.0, (0.0, y))

    validate(module.compile())


def test_nat_args(validate):
    module = GuppyModule("test")
    n = guppy.nat_var("n", module=module)

    @guppy.declare(module)
    def foo(x: array[int, n]) -> array[int, n]: ...

    @guppy(module)
    def main(x: array[int, 42]) -> array[int, 42]:
        return foo(x)


def test_infer_basic(validate):
    module = GuppyModule("test")
    T = guppy.type_var("T", module=module)

    @guppy.declare(module)
    def foo() -> T: ...

    @guppy(module)
    def main() -> None:
        x: int = foo()

    validate(module.compile())


def test_infer_list(validate):
    module = GuppyModule("test")
    T = guppy.type_var("T", module=module)

    @guppy.declare(module)
    def foo() -> T: ...

    @guppy(module)
    def main() -> None:
        xs: list[int] = [foo()]
        ys = [1.0, foo()]

    validate(module.compile())


def test_infer_nested(validate):
    module = GuppyModule("test")
    T = guppy.type_var("T", module=module)

    @guppy.declare(module)
    def foo() -> T: ...

    @guppy.declare(module)
    def bar(x: T) -> T: ...

    @guppy(module)
    def main() -> None:
        x: int = bar(foo())

    validate(module.compile())


def test_infer_left_to_right(validate):
    module = GuppyModule("test")
    S = guppy.type_var("S", module=module)
    T = guppy.type_var("T", module=module)

    @guppy.declare(module)
    def foo() -> T: ...

    @guppy.declare(module)
    def bar(x: T, y: T, z: S, a: tuple[T, S]) -> None: ...

    @guppy(module)
    def main() -> None:
        bar(42, foo(), False, foo())

    validate(module.compile())


def test_type_apply_basic(validate):
    module = GuppyModule("test")
    S = guppy.type_var("S", module=module)
    T = guppy.type_var("T", module=module)

    @guppy.declare(module)
    def foo(x: T) -> T: ...

    @guppy.declare(module)
    def bar(x: S, y: T) -> S: ...

    @guppy(module)
    def main() -> tuple[int, float, float]:
        x = foo[int](0)
        y = foo[float](1.0)
        z = bar[float, int](y, x)
        return x, y, z

    validate(module.compile())


def test_type_apply_higher_order(validate):
    module = GuppyModule("test")
    S = guppy.type_var("S", module=module)
    T = guppy.type_var("T", module=module)

    @guppy.declare(module)
    def foo(x: T) -> T: ...

    @guppy.declare(module)
    def bar(x: S, y: T) -> S: ...

    @guppy(module)
    def main() -> tuple[int, float, float]:
        f = foo[int]
        g = foo[float]
        h = bar[float, int]
        x = f(0)
        y = g(1.0)
        z = h(y, x)
        return x, y, z

    validate(module.compile())


def test_type_apply_nat(validate):
    module = GuppyModule("test")
    n = guppy.nat_var("n", module=module)

    @guppy.declare(module)
    def foo(x: array[int, n]) -> int: ...

    @guppy(module)
    def main() -> int:
        return foo[0](array()) + foo[2](array(1, 2))

    validate(module.compile())


def test_type_apply_empty_tuple(validate):
    module = GuppyModule("test")
    T = guppy.type_var("T", module=module)

    @guppy.declare(module)
    def foo(x: T) -> None:
        ...

    @guppy(module)
    def main() -> None:
        # `()` is the type of an empty tuple (`tuple[]` is not syntactically valid)
        foo[()]

    validate(module.compile())


def test_pass_poly_basic(validate):
    module = GuppyModule("test")
    T = guppy.type_var("T", module=module)

    @guppy.declare(module)
    def foo(f: Callable[[T], T]) -> None: ...

    @guppy.declare(module)
    def bar(x: int) -> int: ...

    @guppy(module)
    def main() -> None:
        foo(bar)

    validate(module.compile())


def test_pass_poly_cross(validate):
    module = GuppyModule("test")
    S = guppy.type_var("S", module=module)
    T = guppy.type_var("T", module=module)

    @guppy.declare(module)
    def foo(f: Callable[[S], int]) -> None: ...

    @guppy.declare(module)
    def bar(x: bool) -> T: ...

    @guppy(module)
    def main() -> None:
        foo(bar)

    validate(module.compile())


def test_linear(validate):
    module = GuppyModule("test")
    module.load_all(quantum)
    T = guppy.type_var("T", copyable=False, droppable=False, module=module)

    @guppy.declare(module)
    def foo(x: T) -> T: ...

    @guppy(module)
    def main(q: qubit) -> qubit:
        return foo(q)

    validate(module.compile())


def test_affine(validate):
    module = GuppyModule("test")
    T = guppy.type_var("T", copyable=False, droppable=True, module=module)

    @guppy.declare(module)
    def foo(x: T) -> T: ...

    @guppy(module)
    def main(a: array[int, 7]) -> None:
        foo(a)

    validate(module.compile())


def test_relevant(validate):
    module = GuppyModule("test")
    T = guppy.type_var("T", copyable=True, droppable=False, module=module)

    @guppy.type(ht.Bool, copyable=True, droppable=False, module=module)
    class R: ...

    @guppy.declare(module)
    def foo(x: T) -> T: ...

    @guppy(module)
    def main(r: R) -> R:
        r_copy = r
        return foo(r_copy)

    validate(module.compile())


def test_pass_nonlinear(validate):
    module = GuppyModule("test")
    module.load_all(quantum)
    T = guppy.type_var("T", copyable=False, droppable=False, module=module)

    @guppy.declare(module)
    def foo(x: T) -> T: ...

    @guppy(module)
    def main(x: int) -> None:
        foo(x)

    validate(module.compile())


def test_pass_linear(validate):
    module = GuppyModule("test")
    module.load_all(quantum)
    T = guppy.type_var("T", copyable=False, droppable=False, module=module)

    @guppy.declare(module)
    def foo(f: Callable[[T], T]) -> None: ...

    @guppy.declare(module)
    def bar(q: qubit) -> qubit: ...

    @guppy(module)
    def main() -> None:
        foo(bar)

    validate(module.compile())


def test_custom_higher_order():
    class CustomCompiler(CustomCallCompiler):
        def compile(self, args: list[Wire]) -> list[Wire]:
            return args

    module = GuppyModule("test")
    T = guppy.type_var("T", module=module)

    @guppy.custom(module, CustomCompiler())
    def foo(x: T) -> T: ...

    @guppy(module)
    def main(x: int) -> int:
        f: Callable[[int], int] = foo
        return f(x)


@pytest.mark.skip("Higher-order polymorphic functions are not yet supported")
def test_higher_order_value(validate):
    module = GuppyModule("test")
    T = guppy.type_var(module, "T")

    @guppy.declare(module)
    def foo(x: T) -> T: ...

    @guppy.declare(module)
    def bar(x: T) -> T: ...

    @guppy(module)
    def main(b: bool) -> int:
        f = foo if b else bar
        return f(42)

    validate(module.compile())
