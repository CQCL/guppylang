from hugr import ops

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from tests.util import compile_guppy


def test_id(validate):
    @compile_guppy
    def identity(x: int) -> int:
        return x

    validate(identity)


def test_void(validate):
    @compile_guppy
    def void() -> None:
        return

    validate(void)


def test_copy(validate):
    @compile_guppy
    def copy(x: int) -> tuple[int, int]:
        return x, x

    validate(copy)


def test_discard(validate):
    @compile_guppy
    def discard(x: int) -> None:
        return

    validate(discard)


def test_implicit_return(validate):
    @compile_guppy
    def ret() -> None:
        pass

    validate(ret)


def test_assign(validate):
    @compile_guppy
    def foo(x: bool) -> bool:
        y = x
        return y

    validate(foo)


def test_assign_expr(validate):
    @compile_guppy
    def foo(x: bool) -> bool:
        (y := x)
        return y

    validate(foo)


def test_func_def_name():
    @compile_guppy
    def func_name() -> None:
        return

    assert func_name.func_defn.f_name == "func_name"


def test_func_decl_name():
    module = GuppyModule("test")

    @guppy.declare(module)
    def func_name() -> None: ...

    hugr = module.compile_hugr()
    [def_op] = [
        data.op for n, data in hugr.nodes() if isinstance(data.op, ops.FuncDecl)
    ]
    assert isinstance(def_op, ops.FuncDecl)
    assert def_op.f_name == "func_name"


def test_compile_again():
    module = GuppyModule("test")

    @guppy(module)
    def identity(x: int) -> int:
        return x

    hugr = module.compile()

    # Compiling again should return the same Hugr
    assert hugr is module.compile()
