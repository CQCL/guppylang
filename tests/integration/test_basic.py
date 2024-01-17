from guppylang.decorator import guppy
from guppylang.hugr import ops
from guppylang.module import GuppyModule


def test_id(validate):
    @guppy(compile=True)
    def identity(x: int) -> int:
        return x

    validate(identity)


def test_void(validate):
    @guppy(compile=True)
    def void() -> None:
        return

    validate(void)


def test_copy(validate):
    @guppy(compile=True)
    def copy(x: int) -> (int, int):
        return x, x

    validate(copy)


def test_discard(validate):
    @guppy(compile=True)
    def discard(x: int) -> None:
        return

    validate(discard)


def test_implicit_return(validate):
    @guppy(compile=True)
    def ret() -> None:
        pass

    validate(ret)


def test_assign(validate):
    @guppy(compile=True)
    def foo(x: bool) -> bool:
        y = x
        return y

    validate(foo)


def test_assign_expr(validate):
    @guppy(compile=True)
    def foo(x: bool) -> bool:
        (y := x)
        return y

    validate(foo)


def test_func_def_name():
    @guppy(compile=True)
    def func_name() -> None:
        return

    [def_op] = [n.op for n in func_name.nodes() if isinstance(n.op, ops.FuncDefn)]
    assert def_op.name == "func_name"


def test_func_decl_name():
    module = GuppyModule("test")

    @guppy.declare(module)
    def func_name() -> None:
        ...

    [def_op] = [
        n.op for n in module.compile().nodes() if isinstance(n.op, ops.FuncDecl)
    ]
    assert def_op.name == "func_name"
